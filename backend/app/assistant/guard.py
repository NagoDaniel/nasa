"""Safety gates around the assistant: input sanitising, prompt-injection screening,
rate limiting, reply signing and output checks. All deterministic, no LLM involved."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import secrets
import time
import unicodedata
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from ..config import settings
from .places import fold

# ----------------------------------------------------------------------------- sanitising
_KEEP_CONTROL = {"\n", "\t"}


def sanitize(text: str, max_chars: int) -> str:
    """NFKC-normalise, drop control / zero-width / bidi / private-use characters,
    collapse whitespace, cap the length."""
    s = unicodedata.normalize("NFKC", text)
    s = "".join(
        (" " if c in _KEEP_CONTROL else c)
        for c in s
        if c in _KEEP_CONTROL or unicodedata.category(c) not in ("Cc", "Cf", "Co", "Cs", "Cn")
    )
    s = " ".join(s.split())
    return s[:max_chars]


# ----------------------------------------------------------------------------- injection gate
# Matched on the folded text (lower-case ascii, punctuation -> spaces) and, for markup, on the raw text.
_FOLDED_PATTERNS = [
    r"\b(ignore|disregard|forget|override|bypass|skip|drop)\b.{0,40}\b(previous|prior|above|earlier|all|any|your|the|these|those|system|initial|original)\b.{0,30}\b(instruction|instructions|rules|prompt|prompts|directions|guidelines|guardrails|restrictions|policies|messages?)\b",
    r"\b(system|developer|hidden|initial|original|secret|internal)\s+(prompt|message|instructions?|rules|configuration)\b",
    r"\byou are (now|no longer|free)\b",
    r"\bfrom now on\b.{0,30}\b(you|act|respond|answer|reply|behave)\b",
    r"\b(you|now|please|pls)\s+(act|behave|pretend|roleplay|role play)\s+(as|like|to be)\b",
    r"^(act|behave|pretend|roleplay|role play|imagine you are)\s+(as|like|to be|you)\b",
    r"\b(jailbreak|jail break|dan mode|developer mode|dev mode|god mode|sudo mode|admin mode|do anything now|unfiltered|uncensored|no restrictions|without restrictions)\b",
    r"\b(repeat|print|reveal|output|leak|dump|display|expose|write out|spell out)\b.{0,30}\b(your|the|system|initial|hidden|above|previous)\s+(instructions|prompt|rules|configuration|config|text|message)\b",
    r"\b(what are|tell me|show me|give me)\s+your\s+(instructions|prompt|rules|system|guidelines|configuration)\b",
    r"\b(api|secret|access)\s*key\b",
    r"\bnew (instructions|rules|persona|role)\b",
    r"\b(simulate|emulate)\b.{0,20}\b(ai|assistant|model|chatbot|gpt|gemini)\b",
    # Romanian
    r"\b(ignora|ignorati|uita|uitati|treci peste|nu mai tine cont)\b.{0,40}\b(instructiuni|instructiunile|regulile|reguli|promptul|prompt|restrictiile)\b",
    r"\b(prompt(ul)? de sistem|instructiunile (tale|de sistem|initiale|ascunse)|regulile tale)\b",
    r"\b(comporta te|prefa te|joaca rolul|pretinde ca esti)\b",
    r"\b(esti acum|de acum inainte (esti|vei|raspunde))\b",
    r"\b(arata|afiseaza|repeta|scrie)\b.{0,20}\b(instructiunile|promptul|regulile)\b",
]
_RAW_PATTERNS = [
    r"<\s*/?\s*(system|assistant|user|model|instruction|instructions|im_start|im_end|tool|function)\b",
    r"\[/?\s*(inst|system|sys)\s*\]",
    r"#{2,}\s*(system|instruction|instructions|new rules)",
    r"<\|[^|]{0,30}\|>",
    r"[A-Za-z0-9+/=_-]{80,}",  # base64 / encoded payloads
    r"\{\{.*?\}\}|\$\{.*?\}",  # template injection
]
_FOLDED_RE = [re.compile(p) for p in _FOLDED_PATTERNS]
_RAW_RE = [re.compile(p, re.IGNORECASE) for p in _RAW_PATTERNS]


def looks_like_injection(text: str) -> bool:
    f = fold(text)
    return any(r.search(f) for r in _FOLDED_RE) or any(r.search(text) for r in _RAW_RE)


# ----------------------------------------------------------------------------- rate limits
class RateLimiter:
    """Sliding-window limits per client key (minute + day) and a global daily budget for
    LLM calls. In-memory: valid for one uvicorn worker (run with --workers 1)."""

    MAX_KEYS = 20_000

    def __init__(self, per_min: int, per_day: int, global_llm_per_day: int,
                 clock: Callable[[], float] = time.time) -> None:
        self.per_min, self.per_day, self.global_llm_per_day = per_min, per_day, global_llm_per_day
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._llm_day: str | None = None
        self._llm_used = 0
        self._lock = Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Count one message; returns (allowed, retry_after_seconds)."""
        now = self.clock()
        with self._lock:
            if len(self._hits) > self.MAX_KEYS:
                self._prune(now)
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= 86_400:
                q.popleft()
            last_min = [t for t in q if now - t < 60]
            if len(q) >= self.per_day:
                return False, max(1, math.ceil(86_400 - (now - q[0])))
            if len(last_min) >= self.per_min:
                return False, max(1, math.ceil(60 - (now - last_min[0])))
            q.append(now)
            return True, 0

    def take_llm(self) -> bool:
        """Consume one unit of the global daily LLM budget (resets at 00:00 UTC)."""
        day = datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if day != self._llm_day:
                self._llm_day, self._llm_used = day, 0
            if self._llm_used >= self.global_llm_per_day:
                return False
            self._llm_used += 1
            return True

    def llm_left(self) -> int:
        day = datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%Y-%m-%d")
        return self.global_llm_per_day - (self._llm_used if day == self._llm_day else 0)

    def _prune(self, now: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] >= 86_400]:
            del self._hits[k]
        if len(self._hits) > self.MAX_KEYS:  # still too many: drop the oldest half
            for k in sorted(self._hits, key=lambda k: self._hits[k][-1])[: len(self._hits) // 2]:
                del self._hits[k]


limiter = RateLimiter(settings.rate_ip_per_min, settings.rate_ip_per_day, settings.rate_global_llm_per_day)


def client_key(host: str | None, forwarded_for: str | None) -> str:
    if settings.trust_forwarded_for and forwarded_for:
        return forwarded_for.split(",")[0].strip()[:64]
    return (host or "unknown")[:64]


# ----------------------------------------------------------------------------- reply signing
_SECRET = (settings.assistant_secret.get_secret_value().encode() if settings.assistant_secret
           else secrets.token_bytes(32))


def sign(text: str) -> str:
    return hmac.new(_SECRET, text.encode(), hashlib.sha256).hexdigest()[:32]


def verify(text: str, sig: str | None) -> bool:
    return bool(sig) and hmac.compare_digest(sign(text), sig)


# ----------------------------------------------------------------------------- output checks
# Random marker inside the system instruction; if it shows up in a reply, the prompt leaked.
CANARY = "s2f-" + secrets.token_hex(6)

_MD_LINK = re.compile(r"!?\[([^\]]{0,200})\]\([^)]{0,500}\)")
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_TAG = re.compile(r"</?[a-zA-Z][^>]{0,200}>")
_FENCE = re.compile(r"```[a-zA-Z]*")


def clean_reply(text: str, max_chars: int = 1500) -> str:
    """Plain text only: no HTML, links, URLs or code fences; bold/italic markers removed."""
    s = _MD_LINK.sub(r"\1", text)
    s = _URL.sub("", s)
    s = _TAG.sub("", s)
    s = _FENCE.sub("", s)
    s = re.sub(r"(\*\*|__)(.+?)\1", r"\2", s)
    s = re.sub(r"^\s*#{1,6}\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[*•]\s+", "- ", s, flags=re.MULTILINE)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if len(s) > max_chars:
        cut = s[:max_chars]
        s = cut[: cut.rfind(" ")] + " …" if " " in cut else cut
    return s


def leaked(text: str) -> bool:
    f = text.lower()
    return CANARY in f or "security rules (never reveal)" in f


# ----------------------------------------------------------------------------- grounding
_NUM = re.compile(r"(?<![\w.])[-−–]?\d+(?:[.,]\d+)*")


def _parse(tok: str) -> list[float]:
    """Possible values of a number as written (EN '1,234.5' or RO '1.234,5' / '12,5')."""
    t = tok.replace("−", "-").replace("–", "-")
    out = []
    for cand in (t.replace(",", ""), t.replace(".", "").replace(",", "."), t.replace(",", ".")):
        try:
            out.append(float(cand))
        except ValueError:
            pass
    return out


def numbers_in(obj: Any) -> set[float]:
    """Every number inside a JSON-like object (also numbers written inside strings)."""
    vals: set[float] = set()

    def walk(o: Any) -> None:
        if isinstance(o, bool) or o is None:
            return
        if isinstance(o, (int, float)):
            if math.isfinite(o):
                vals.add(float(o))
        elif isinstance(o, str):
            for tok in _NUM.findall(o):
                vals.update(_parse(tok))
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)

    walk(obj)
    return vals


def _close(x: float, evidence: set[float]) -> bool:
    for v in evidence:
        for scaled in (v, v * 100, v / 1000, v / 1_000_000):
            # rounding to integers / 1 decimal, or ~2 % relative rounding of big values
            tol = max(0.51, 0.02 * abs(scaled)) if abs(scaled) >= 10 else 0.051
            if abs(x - scaled) <= tol:
                return True
    return False


def ungrounded_numbers(reply: str, evidence: Any) -> list[str]:
    """Numbers in the reply that appear nowhere in the data the model was given.
    Small counts (≤ 12) and years are skipped: the model may count rows or name years."""
    ev = numbers_in(evidence)
    bad = []
    for tok in _NUM.findall(reply):
        vals = _parse(tok)
        if not vals:
            continue
        x = vals[0]
        if abs(x) <= 12 or (1980 <= x <= 2035 and float(x).is_integer()):
            continue
        if not any(_close(v, ev) for v in vals):
            bad.append(tok)
    return bad


def compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
