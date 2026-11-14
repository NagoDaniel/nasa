"""Deterministic answers that need no language model: greetings, help, "zoom to <place>",
"open <section>", a bare place name (selects it and shows a short data card)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import datasets as ds
from . import places
from .places import Place, fold
from .tools import _latest_hazards, _soil_brief

Lang = str


@dataclass
class RuleReply:
    reply: str
    actions: list[dict] = field(default_factory=list)
    choices: list[Place] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------- language
_RO_WORDS = {"salut", "buna", "arata", "mergi", "du", "deschide", "judet", "judetul", "comuna", "ce", "cum", "unde",
             "multumesc", "mersi", "ajutor", "vreau", "rog", "care", "este", "sunt", "pentru", "si", "sau", "anul",
             "zile", "ploaie", "seceta", "porumb", "grau", "orz", "ovaz", "mazare", "naut", "floarea", "soarelui",
             "in", "din", "la", "pe", "cat", "cate", "poti", "selecteaza", "gaseste", "harta", "solul", "culturi"}
_EN_WORDS = {"the", "show", "what", "how", "zoom", "please", "go", "open", "hi", "hello", "thanks", "which", "is",
             "are", "my", "me", "can", "you", "where", "help", "of", "for", "and", "heat", "days", "rain", "soil"}


def detect_lang(text: str, default: Lang) -> Lang:
    words = set(fold(text).split())
    ro, en = len(words & _RO_WORDS), len(words & _EN_WORDS)
    # Romanian letters in lower-case words (place names are capitalised, so "Sebeș" does not count)
    ro += 2 * sum(1 for w in re.findall(r"\b[a-zăâîșțşţ][\wăâîșțşţ-]*", text) if re.search(r"[ăâîșțşţ]", w))
    if ro > en:
        return "ro"
    if en > ro:
        return "en"
    return default


# ----------------------------------------------------------------------------- canned texts
T = {
    "hello": {
        "en": "Hi! I'm the SPACE2FEED assistant. I answer from this dashboard's data (NASA Earth observation, soil, crop statistics) and can move the map for you. Try: \"zoom to Aiud\", \"heat at maize flowering in Alba in 2024\", \"compare maize–wheat–maize with pea–wheat–sunflower here\" or \"where is pea supply most reliable?\"",
        "ro": "Bună! Sunt asistentul SPACE2FEED. Răspund din datele acestui panou (observații NASA, sol, statistici de culturi) și pot muta harta pentru dvs. Încercați: „du-mă la Aiud”, „căldură la înflorirea porumbului în Alba în 2024”, „compară porumb–grâu–porumb cu mazăre–grâu–floarea-soarelui aici” sau „unde e aprovizionarea cu mazăre cea mai sigură?”",
    },
    "thanks": {
        "en": "You're welcome! Ask me anything else about the data or the map.",
        "ro": "Cu plăcere! Întrebați-mă orice altceva despre date sau hartă.",
    },
    "help": {
        "en": "I can:\n- find a county or commune and zoom the map to it (\"zoom to Sebeș\")\n- open a section (\"open soil\", \"open rotations\", \"open sourcing\")\n- answer from the data: rain, heat, soil moisture, vegetation, season risks, soil, crop statistics\n- compare 2–3 rotations for the selected area with your priorities\n- summarise availability, quality and impact of an ingredient crop per county\nI only use this project's data and always say the period, source and confidence. I can misread a question, so check the numbers in the panel.",
        "ro": "Pot să:\n- găsesc un județ sau o comună și să măresc harta acolo („du-mă la Sebeș”)\n- deschid o secțiune („deschide solul”, „deschide rotațiile”, „deschide aprovizionarea”)\n- răspund din date: ploaie, căldură, umiditatea solului, vegetație, riscuri sezoniere, sol, statistici de culturi\n- compar 2–3 rotații pentru zona selectată după prioritățile dvs.\n- rezum disponibilitatea, calitatea și impactul unui ingredient pe județe\nFolosesc doar datele proiectului și spun mereu perioada, sursa și încrederea. Pot înțelege greșit o întrebare, deci verificați cifrele din panou.",
    },
    "refused": {
        "en": "Sorry, I can only help with the SPACE2FEED dashboard and its data. Ask me about weather, soil, crops, rotations or sourcing for an area in the study region.",
        "ro": "Îmi pare rău, pot ajuta doar cu panoul SPACE2FEED și datele sale. Întrebați-mă despre vreme, sol, culturi, rotații sau aprovizionare pentru o zonă din regiunea de studiu.",
    },
    "limited": {
        "en": "You're sending messages a bit fast. Please wait {n} s and try again.",
        "ro": "Trimiteți mesaje puțin prea repede. Vă rog așteptați {n} s și încercați din nou.",
    },
    "budget": {
        "en": "The AI part has reached its daily limit. I can still navigate: type a county or commune name, or \"open soil\", \"open rotations\".",
        "ro": "Partea AI și-a atins limita zilnică. Pot încă naviga: scrieți numele unui județ sau al unei comune, sau „deschide solul”, „deschide rotațiile”.",
    },
    "offline": {
        "en": "The AI part is not available right now. I can still navigate: type a county or commune name, or \"open soil\", \"open rotations\", \"open sourcing\".",
        "ro": "Partea AI nu este disponibilă acum. Pot încă naviga: scrieți numele unui județ sau al unei comune, sau „deschide solul”, „deschide rotațiile”, „deschide aprovizionarea”.",
    },
    "busy": {
        "en": "I'm busy with other questions right now. Please try again in a few seconds.",
        "ro": "Sunt ocupat cu alte întrebări acum. Vă rog încercați din nou în câteva secunde.",
    },
    "empty": {
        "en": "Please type a question.",
        "ro": "Vă rog scrieți o întrebare.",
    },
    "which": {
        "en": "Several areas are called {name}. Which one do you mean?",
        "ro": "Mai multe zone se numesc {name}. Pe care o aveți în vedere?",
    },
    "outside": {
        "en": "{name} is outside the study area. This dashboard covers Alba and its neighbours: Arad, Bihor, Cluj, Hunedoara, Mureș, Sibiu and Vâlcea.",
        "ro": "{name} este în afara zonei de studiu. Panoul acoperă Alba și județele vecine: Arad, Bihor, Cluj, Hunedoara, Mureș, Sibiu și Vâlcea.",
    },
    "section": {
        "en": "Opened {label}.",
        "ro": "Am deschis {label}.",
    },
}


def text(key: str, lang: Lang, **kw) -> str:
    return T[key][lang if lang in ("en", "ro") else "en"].format(**kw)


# ----------------------------------------------------------------------------- patterns
_GREETING = re.compile(r"^(hi|hello|hey|hei|salut|salutare|buna|buna ziua|buna seara|neata|good (morning|afternoon|evening)|servus)( there| assistant| asistent)?$")
_THANKS = re.compile(r"^(thanks|thank you|thx|ty|merci|mersi|multumesc|multumim|ms)( (a lot|very much|so much|mult|frumos))?$")
_HELP = re.compile(r"^(help|ajutor|what can you do|how does this work|how do i use this|ce poti face|ce stii sa faci|cum functioneaza|cum te folosesc)$")
_NAV = re.compile(
    r"^(?:please |pls |te rog )?(?:can you |could you |poti sa |poti )?"
    r"(?:zoom(?: in)?(?: to| on| into| in on)?|go to|go|take me to|bring me to|fly to|navigate to|jump to|switch to|open|show(?: me)?|"
    r"select|find|locate|where is|du ma la|du ma in|du ma pe|mergi la|mergi in|mergi pe|deschide|arata(?: mi)?|selecteaza|gaseste|"
    r"unde (?:este|e)|zoom pe|treci la|focus on)\s+(?P<rest>.+)$"
)
_TRAIL = re.compile(r"\s+(please|pls|te rog|on the map|pe harta|now|acum|section|tab|page|sectiunea|sectiune|view)$")
_LEAD = re.compile(r"^(the|la|sectiunea|section|pagina|tab)\s+")

SECTION_WORDS = {
    "overview": ["overview", "summary", "prezentare", "prezentare generala", "rezumat", "home", "start"],
    "weather": ["weather", "weather and water", "water", "vremea", "vreme", "apa", "vreme si apa", "vremea si apa", "meteo", "indicators", "indicatori"],
    "risks": ["risks", "season risks", "seasonal risks", "hazards", "riscuri", "riscurile", "riscuri sezoniere", "risk"],
    "soil": ["soil", "soils", "sol", "solul"],
    "crops": ["crops", "crop mix", "culturi", "culturile"],
    "rotations": ["rotations", "rotation", "crop rotation", "crop rotations", "rotatii", "rotatiile", "asolament"],
    "sourcing": ["sourcing", "sourcing map", "procurement", "aprovizionare", "aprovizionarea", "achizitii", "harta aprovizionarii"],
    "recs": ["recommendations", "recs", "recomandari", "recomandarile"],
    "trends": ["trends", "trends and data", "tendinte", "tendintele", "tendinte si date"],
}
_SECTION_OF = {w: s for s, ws in SECTION_WORDS.items() for w in ws}
SECTION_LABEL = {
    "en": {"overview": "the overview", "weather": "Weather & water", "risks": "Season risks", "soil": "Soil", "crops": "Crops",
           "rotations": "Rotations", "sourcing": "the sourcing map", "recs": "Recommendations", "trends": "Trends & data"},
    "ro": {"overview": "prezentarea generală", "weather": "Vreme și apă", "risks": "Riscuri sezoniere", "soil": "Solul", "crops": "Culturile",
           "rotations": "Rotațiile", "sourcing": "harta aprovizionării", "recs": "Recomandările", "trends": "Tendințe și date"},
}

_outside_cache: dict = {}


def _outside_counties() -> dict[str, str]:
    """{folded name: name} of Romanian counties outside the study area (from the boundary layer)."""
    if "names" not in _outside_cache:
        inside = {u["id"] for u in ds.units_index().values() if u["kind"] == "county"}
        try:
            fc = ds.store.get("geo/counties.geojson.json")
            _outside_cache["names"] = {fold(f["properties"]["name"]): f["properties"]["name"]
                                       for f in fc["features"] if f["properties"].get("code") not in inside}
        except FileNotFoundError:
            _outside_cache["names"] = {}
    return _outside_cache["names"]


# ----------------------------------------------------------------------------- area card
def area_card(p: Place, lang: Lang) -> RuleReply:
    u = ds.require_unit(p.id)
    ro = lang == "ro"
    if p.kind == "county":
        head = f"{p.name} — {'județ' if ro else 'county'}, {u['area_km2']:,.0f} km²."
    else:
        head = (f"{p.name} — comună/oraș în județul {p.county_name}, {u['area_km2']:,.0f} km²." if ro
                else f"{p.name} — commune/town in {p.county_name} county, {u['area_km2']:,.0f} km².")
    lines = [head + (" Am selectat-o pe hartă." if ro else " I've selected it on the map.")]
    sources = []
    s = _soil_brief(p.id)
    if s and s.get("ph") is not None:
        lines.append(f"- {'Sol' if ro else 'Soil'} (SoilGrids, 0–30 cm): {s['texture']}, pH {s['ph']}, "
                     f"{'carbon organic' if ro else 'organic carbon'} {s['soc_g_kg']} g/kg.")
        sources.append("ISRIC SoilGrids 2.0")
    h = _latest_hazards(p.id)
    if h["latest_year_with_data"]:
        hits = "; ".join(h["hazards_hit"]) or ("niciun prag de risc depășit" if ro else "no hazard threshold crossed")
        lines.append(f"- {'Ultimul sezon cu date meteo' if ro else 'Latest season with weather data'} ({h['latest_year_with_data']}): {hits}.")
        sources.append("NASA POWER + GLDAS")
    cm = ds.cropmap(p.id)
    if cm and cm.get("values"):
        y = max(cm["values"])
        classes = {c: n for c, n in cm["values"][y].items() if 200 <= int(c) < 300}
        tot = sum(classes.values())
        if tot:
            top = sorted(classes.items(), key=lambda x: -x[1])[:3]
            mix = ", ".join(f"{cm['classes'][c]} {100 * n / tot:.0f}%" for c, n in top)
            lines.append(f"- {'Culturi principale' if ro else 'Main crops'} ({y}, EUCROPMAP): {mix}.")
            sources.append("JRC EUCROPMAP")
    conf = ("Încredere: solul se potrivește comunei; vremea vine din celule de 25–50 km (regională)." if ro and p.kind == "commune"
            else "Confidence: soil fits the commune; weather comes from 25–50 km cells (regional)." if p.kind == "commune"
            else "Încredere: medie pentru județ (grile regionale)." if ro else "Confidence: medium at county level (regional grids).")
    lines.append(conf)
    lines.append("Întrebați-mă despre vreme, riscuri, sol sau rotații aici." if ro else "Ask me about weather, risks, soil or rotations here.")
    return RuleReply("\n".join(lines), [{"type": "select_area", "unit_id": p.id}], sources=sources)


def _place_reply(phrase: str, lang: Lang, fuzzy: bool = True) -> RuleReply | None:
    hits = places.resolve(phrase, fuzzy=fuzzy)
    if len(hits) == 1:
        return area_card(hits[0], lang)
    if len(hits) > 1:
        return RuleReply(text("which", lang, name=hits[0].name), choices=hits)
    out = _outside_counties().get(places.strip_prefixes(fold(phrase)))
    if out:
        return RuleReply(text("outside", lang, name=out))
    return None


def route(message: str, lang: Lang) -> RuleReply | None:
    """A reply when the message is a simple command; None means 'needs the language model'."""
    f = fold(message)
    if not f:
        return None
    if _GREETING.match(f):
        return RuleReply(text("hello", lang))
    if _THANKS.match(f):
        return RuleReply(text("thanks", lang))
    if _HELP.match(f):
        return RuleReply(text("help", lang))
    sec = _SECTION_OF.get(f)
    m = _NAV.match(f)
    if m:
        rest = m.group("rest")
        for _ in range(3):
            rest = _TRAIL.sub("", _LEAD.sub("", rest)).strip()
        sec = _SECTION_OF.get(rest)
        if not sec:
            return _place_reply(rest, lang)
    if sec:
        return RuleReply(text("section", lang, label=SECTION_LABEL[lang][sec]), [{"type": "open_section", "section": sec}])
    if len(f.split()) <= 4:  # a bare place name (typo tolerance only for short phrases)
        return _place_reply(message, lang, fuzzy=len(f.split()) <= 2)
    return None
