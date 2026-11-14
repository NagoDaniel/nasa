"""Deterministic place-name resolution over the analysis units (8 counties + 662 communes).

Matching ignores case, diacritics (ș/ş, ț/ţ, ă, â, î all fold to ascii), punctuation and
prefixes such as "comuna", "municipiul", "județul". Several communes share a name
(Ineu, Lunca, Roșia…), so lookups return every match and the caller asks the user to pick.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

from .. import datasets as ds

PREFIXES = (
    "comuna", "com", "municipiul", "municipiu", "mun", "orasul", "oras", "judetul", "judet", "jud",
    "county", "commune", "municipality", "town", "city", "of", "the", "village", "satul",
)
_CEDILLA = str.maketrans({"ş": "s", "Ş": "s", "ţ": "t", "Ţ": "t", "ș": "s", "Ș": "s", "ț": "t", "Ț": "t"})


def fold(text: str) -> str:
    """Lower-case ascii form used for every comparison."""
    s = unicodedata.normalize("NFKD", text.translate(_CEDILLA))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def strip_prefixes(folded: str) -> str:
    words = folded.split()
    while words and words[0] in PREFIXES:
        words = words[1:]
    while words and words[-1] in ("county", "commune", "judet", "judetul", "comuna"):
        words = words[:-1]
    return " ".join(words)


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    kind: str  # county | commune
    county: str
    county_name: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


_cache: dict = {"src": None, "index": None}


def _index() -> tuple[dict[str, list[Place]], dict[str, Place], dict[str, Place]]:
    """{folded name: [places]}, {county code: place}, {id: place}; rebuilt when units.json is reloaded."""
    units = ds.store.get("units.json")
    if _cache["src"] is units:
        return _cache["index"]
    by_id = {u["id"]: u for u in units["units"]}
    county_names = {u["id"]: u["name"] for u in units["units"] if u["kind"] == "county"}
    names: dict[str, list[Place]] = {}
    codes: dict[str, Place] = {}
    ids: dict[str, Place] = {}
    for u in by_id.values():
        p = Place(u["id"], u["name"], u["kind"], u["county"], county_names.get(u["county"], u["county"]))
        ids[p.id] = p
        names.setdefault(fold(u["name"]), []).append(p)
        if u["kind"] == "county":
            codes[u["id"]] = p
    # Counties first, so "Sibiu" means the county before the city of the same name.
    for k in names:
        names[k].sort(key=lambda p: (p.kind != "county", p.county_name, p.name))
    _cache.update(src=units, index=(names, codes, ids))
    return names, codes, ids


def place(uid: str) -> Place | None:
    return _index()[2].get(uid)


def resolve(query: str, fuzzy: bool = True, limit: int = 6) -> list[Place]:
    """All units matching a place phrase. County match wins over a same-named city
    unless the phrase says city/municipiul/oraș/commune."""
    names, codes, _ = _index()
    raw = query.strip()
    if re.fullmatch(r"[A-Za-z]{2}", raw) and raw.upper() in codes:
        return [codes[raw.upper()]]
    f = fold(raw)
    if not f:
        return []
    wants_town = bool(re.match(r"(municipiul|municipiu|mun|orasul|oras|city|town|comuna|commune|com)\b", f))
    wants_county = bool(re.match(r"(judetul|judet|jud|county)\b", f)) or f.endswith(" county")
    key = strip_prefixes(f)
    hits = list(names.get(key, []))
    if not hits and fuzzy and len(key) >= 4:
        for k in difflib.get_close_matches(key, list(names), n=3, cutoff=0.85):
            hits += names[k]
    if wants_town:
        hits = [p for p in hits if p.kind == "commune"] or hits
    elif wants_county or any(p.kind == "county" for p in hits):
        counties = [p for p in hits if p.kind == "county"]
        hits = counties or hits
    return hits[:limit]


def find_in_text(text: str) -> list[Place]:
    """Exact (non-fuzzy) place names inside free text; the longest phrase wins.
    Only used when the user explicitly asks to navigate, to avoid matching ordinary words."""
    names = _index()[0]
    words = fold(text).split()
    for n in range(min(4, len(words)), 0, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i + n])
            if phrase in names and phrase not in PREFIXES:
                return resolve(phrase, fuzzy=False)
    return []
