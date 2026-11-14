"""Gemini tool-calling loop. The model only (1) chooses read-only tools and (2) words the
answer from their results. Bounded: max rounds, max calls per round, timeout, concurrency."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config import settings
from . import tools
from .prompts import system_instruction

log = logging.getLogger(__name__)

MAX_CALLS_PER_ROUND = 6
MAX_OUTPUT_TOKENS = 800


class LLMError(Exception):
    """Gemini unavailable, blocked, quota exceeded or timed out (message is safe to log)."""

    def __init__(self, kind: str, msg: str = "") -> None:
        super().__init__(f"{kind}: {msg}")
        self.kind = kind  # unavailable | quota | blocked | timeout | error


@dataclass
class LLMResult:
    reply: str
    actions: list[dict] = field(default_factory=list)
    evidence: list[Any] = field(default_factory=list)  # every tool result, for the grounding check
    tools_used: list[str] = field(default_factory=list)


class Backend(Protocol):
    """Minimal interface, so tests can swap in a fake model."""

    async def generate(self, system: str, contents: list[dict], allow_tools: bool) -> dict: ...


class GeminiBackend:
    """Talks to Gemini via the official google-genai SDK. Returns
    {"text": str | None, "calls": [{"name", "args"}], "content": <model turn>, "blocked": bool}."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        self.types = types
        self.model = model
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(settings.llm_timeout_s * 1000)))
        self.tool = types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in tools.declarations()])
        cats = ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        self.safety = [types.SafetySetting(category=c, threshold="BLOCK_MEDIUM_AND_ABOVE") for c in cats]

    def _content(self, c: dict):
        t = self.types
        if "model_content" in c:  # the model's own turn, passed back unchanged
            return c["model_content"]
        if c["role"] == "tool":
            return t.Content(role="user", parts=[t.Part.from_function_response(name=r["name"], response={"result": r["result"]})
                                                 for r in c["results"]])
        return t.Content(role="model" if c["role"] == "assistant" else "user", parts=[t.Part(text=c["text"])])

    async def generate(self, system: str, contents: list[dict], allow_tools: bool) -> dict:
        t = self.types
        from google.genai import errors

        cfg = t.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            safety_settings=self.safety,
            tools=[self.tool],
            tool_config=t.ToolConfig(function_calling_config=t.FunctionCallingConfig(mode="AUTO" if allow_tools else "NONE")),
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
        )
        if settings.gemini_thinking_budget >= 0:  # -1 = leave the model's default (e.g. Pro models cannot disable thinking)
            cfg.thinking_config = t.ThinkingConfig(thinking_budget=settings.gemini_thinking_budget)
        try:
            resp = await self.client.aio.models.generate_content(model=self.model, contents=[self._content(c) for c in contents], config=cfg)
        except errors.APIError as e:
            raise LLMError("quota" if e.code == 429 else "error", f"HTTP {e.code}") from None
        if resp.prompt_feedback and resp.prompt_feedback.block_reason:
            return {"text": None, "calls": [], "content": None, "blocked": True}
        cand = resp.candidates[0] if resp.candidates else None
        if cand is None or cand.content is None:
            fr = str(getattr(cand, "finish_reason", "")) if cand else ""
            return {"text": None, "calls": [], "content": None, "blocked": "SAFETY" in fr or "PROHIBITED" in fr}
        calls = [{"name": fc.name, "args": dict(fc.args or {})} for fc in (resp.function_calls or [])]
        text = "".join(p.text for p in (cand.content.parts or []) if getattr(p, "text", None) and not getattr(p, "thought", False))
        return {"text": text or None, "calls": calls, "content": cand.content, "blocked": False}


_backend: Backend | None = None
_sem: asyncio.Semaphore | None = None


def backend() -> Backend | None:
    global _backend
    if _backend is None and settings.gemini_api_key:
        _backend = GeminiBackend(settings.gemini_api_key.get_secret_value(), settings.gemini_model)
    return _backend


def semaphore() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(settings.llm_concurrency)
    return _sem


async def run(be: Backend, message: str, history: list[dict], state: dict) -> LLMResult:
    """history: [{"role": "user"|"assistant", "text": str}] (already sanitised and verified)."""
    system = system_instruction(state)
    contents: list[dict] = [{"role": h["role"], "text": h["text"]} for h in history]
    contents.append({"role": "user", "text": message})
    tool_state: dict = {"actions": []}
    res = LLMResult(reply="")

    async def loop() -> None:
        for rnd in range(settings.llm_max_rounds + 1):
            out = await be.generate(system, contents, allow_tools=rnd < settings.llm_max_rounds)
            if out["blocked"]:
                raise LLMError("blocked")
            if not out["calls"]:
                res.reply = out["text"] or ""
                return
            contents.append({"model_content": out["content"]})
            results = []
            for call in out["calls"][:MAX_CALLS_PER_ROUND]:
                r = tools.execute(call["name"], call["args"], tool_state)
                res.tools_used.append(call["name"])
                res.evidence.append(r)
                results.append({"name": call["name"], "result": r})
            contents.append({"role": "tool", "results": results})
        raise LLMError("error", "no final answer")

    try:
        await asyncio.wait_for(loop(), timeout=settings.llm_timeout_s * 1.5)
    except asyncio.TimeoutError:
        raise LLMError("timeout") from None
    res.actions = tool_state["actions"]
    return res
