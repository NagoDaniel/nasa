"""Request / response models of the assistant API. Strict: unknown fields are rejected
and every string has a length cap."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from ..config import settings
from .tools import B_CROPS, SECTIONS

MAX_REPLY = 2000


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Turn(Strict):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=MAX_REPLY)
    sig: str | None = Field(None, max_length=64)


class Context(Strict):
    unit_id: str | None = Field(None, max_length=12, pattern=r"^[A-Z]{1,2}(-\d{4})?$")
    role: Literal["farmer", "procurement"] = "farmer"
    section: Literal[SECTIONS] = "overview"  # type: ignore[valid-type]
    lang: Literal["en", "ro"] = "en"


class ChatRequest(Strict):
    message: str = Field(min_length=1, max_length=settings.assistant_max_chars)
    history: list[Turn] = Field(default_factory=list, max_length=settings.assistant_max_history * 2)
    context: Context = Context()


class SelectArea(Strict):
    type: Literal["select_area"]
    unit_id: str


class OpenSection(Strict):
    type: Literal["open_section"]
    section: Literal[SECTIONS]  # type: ignore[valid-type]


class ColorMap(Strict):
    type: Literal["color_map"]
    kind: Literal["indicator", "agro", "soil", "cropshare"]
    key: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    year: str | None = Field(None, pattern=r"^\d{4}$")


class SetProcurementCrop(Strict):
    type: Literal["set_procurement_crop"]
    crop: Literal[B_CROPS]  # type: ignore[valid-type]
    metric: Literal["availability", "quality", "impact"] | None = None


Action = Annotated[Union[SelectArea, OpenSection, ColorMap, SetProcurementCrop], Field(discriminator="type")]


class Choice(Strict):
    id: str
    name: str
    kind: str
    county_name: str


class ChatResponse(Strict):
    reply: str
    sig: str
    mode: Literal["rule", "llm", "refused", "limited", "offline"]
    actions: list[Action] = Field(default_factory=list)
    choices: list[Choice] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    unverified: list[str] = Field(default_factory=list)  # numbers not found in the tool data
