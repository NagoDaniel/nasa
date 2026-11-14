"""POST /api/assistant/chat — the dashboard assistant.

Pipeline (each step can end the request):
  rate limit → sanitise → injection gate → verify history → deterministic intents
  → global LLM budget → Gemini with read-only tools → output checks → signed reply
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import TypeAdapter, ValidationError

from ..config import settings
from . import guard, intents, llm, places
from .intents import RuleReply, text
from .schemas import Action, ChatRequest, ChatResponse, Choice
from .tools import catalog

router = APIRouter(tags=["assistant"])
log = logging.getLogger("app.assistant")
STATS: Counter = Counter()  # counts only, never message content
_action = TypeAdapter(Action)

UNVERIFIED = {
    "en": "⚠ Some figures could not be matched to the dashboard data — please check them in the panel.",
    "ro": "⚠ Unele cifre nu au putut fi verificate în datele panoului — vă rog verificați-le în panou.",
}
NO_ANSWER = {
    "en": "Sorry, I couldn't find an answer to that in the dashboard data. Try asking about a specific area, crop or indicator.",
    "ro": "Îmi pare rău, nu am găsit un răspuns în datele panoului. Încercați să întrebați despre o anumită zonă, cultură sau indicator.",
}


def _respond(reply: str, mode: str, status: int = 200, headers: dict | None = None, **kw: Any) -> ORJSONResponse:
    STATS[mode] += 1
    body = ChatResponse(reply=reply, sig=guard.sign(reply), mode=mode, **kw)  # type: ignore[arg-type]
    return ORJSONResponse(body.model_dump(), status_code=status, headers=headers)


def _rule(r: RuleReply, mode: str = "rule", prefix: str | None = None) -> ORJSONResponse:
    reply = f"{prefix}\n\n{r.reply}" if prefix else r.reply
    return _respond(reply, mode, actions=_valid_actions(r.actions),
                    choices=[Choice(id=p.id, name=p.name, kind=p.kind, county_name=p.county_name) for p in r.choices],
                    sources=r.sources)


def _valid_actions(raw: list[dict]) -> list:
    out = []
    for a in raw[:3]:
        try:
            act = _action.validate_python(a)
        except ValidationError:
            continue
        if act.type == "select_area" and places.place(act.unit_id) is None:
            continue
        out.append(act)
    return out


def _history(turns: list, max_turns: int) -> list[dict]:
    """Keep verified assistant turns and clean user turns; must start with a user turn."""
    out: list[dict] = []
    for t in turns[-max_turns:]:
        if t.role == "assistant":
            if not guard.verify(t.text, t.sig):
                STATS["forged_history"] += 1
                continue
            txt = t.text
        else:
            txt = guard.sanitize(t.text, settings.assistant_max_chars)
            if not txt or guard.looks_like_injection(txt):
                continue
        if out and out[-1]["role"] == t.role:
            out[-1]["text"] += "\n" + txt
        else:
            out.append({"role": t.role, "text": txt})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _sources(evidence: list[Any]) -> list[str]:
    seen: list[str] = []
    for e in evidence:
        if not isinstance(e, dict):
            continue
        srcs = e.get("sources") if isinstance(e.get("sources"), list) else [e.get("source")]
        for s in srcs:
            if isinstance(s, dict):
                s = "; ".join(str(v) for v in s.values())
            if isinstance(s, str) and s and s not in seen:
                seen.append(s[:160])
    return seen[:5]


@router.get("/assistant/status")
def status() -> dict:
    return {
        "llm": bool(settings.gemini_api_key),
        "max_chars": settings.assistant_max_chars,
        "limits": {"per_minute": settings.rate_ip_per_min, "per_day": settings.rate_ip_per_day},
        "llm_available_today": guard.limiter.llm_left() > 0,
    }


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    t0 = time.perf_counter()
    lang_ui = req.context.lang

    # 1. rate limit per client
    ok, retry = guard.limiter.hit(guard.client_key(request.client.host if request.client else None,
                                                   request.headers.get("x-forwarded-for")))
    if not ok:
        return _respond(text("limited", lang_ui, n=retry), "limited", 429, {"Retry-After": str(retry)})

    # 2. sanitise + 3. injection gate
    msg = guard.sanitize(req.message, settings.assistant_max_chars)
    lang = intents.detect_lang(msg, lang_ui)
    if not msg:
        return _respond(text("empty", lang), "refused")
    if guard.looks_like_injection(msg):
        log.info("assistant refused (injection pattern)")
        return _respond(text("refused", lang), "refused")

    # 4. deterministic answers
    r = intents.route(msg, lang)
    if r is not None:
        return _rule(r)

    # 5. language model (if configured and within budget)
    be = llm.backend()
    if be is None:
        return _offline(msg, lang, "offline")
    if not guard.limiter.take_llm():
        return _offline(msg, lang, "budget")

    unit = places.place(req.context.unit_id) if req.context.unit_id else None
    state = {"lang": lang, "role": req.context.role, "section": req.context.section,
             "unit": unit.as_dict() if unit else None}
    sem = llm.semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), 10)
    except asyncio.TimeoutError:
        return _respond(text("busy", lang), "limited", 503, {"Retry-After": "5"})
    try:
        res = await llm.run(be, msg, _history(req.history, settings.assistant_max_history), state)
    except llm.LLMError as e:
        log.warning("assistant LLM failure: %s", e.kind)
        STATS[f"llm_{e.kind}"] += 1
        if e.kind == "blocked":
            return _respond(text("refused", lang), "refused")
        return _offline(msg, lang, "budget" if e.kind == "quota" else "offline")
    finally:
        sem.release()

    # 6. output checks
    reply = guard.clean_reply(res.reply)
    if guard.leaked(res.reply):
        STATS["leak_blocked"] += 1
        return _respond(text("refused", lang), "refused")
    if not reply:
        reply = NO_ANSWER[lang]
    bad = guard.ungrounded_numbers(reply, [res.evidence, msg, catalog()])
    if bad:
        STATS["unverified"] += 1
        reply = f"{reply}\n\n{UNVERIFIED[lang]}"
    log.info("assistant llm reply in %.1f s, tools=%s, unverified=%d", time.perf_counter() - t0, res.tools_used, len(bad))
    return _respond(reply, "llm", actions=_valid_actions(res.actions), sources=_sources(res.evidence), unverified=bad[:10])


def _offline(msg: str, lang: str, kind: str) -> ORJSONResponse:
    """No LLM: still navigate if the message names exactly one place."""
    hits = places.find_in_text(msg)
    if len(hits) == 1:
        return _rule(intents.area_card(hits[0], lang), "offline", prefix=text(kind, lang))
    if len(hits) > 1:
        return _rule(RuleReply(text("which", lang, name=hits[0].name), choices=hits), "offline", prefix=text(kind, lang))
    return _respond(text(kind, lang), "offline")

