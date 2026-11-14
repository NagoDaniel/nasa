"""App-state tables (SQLite). NASA / geo data lives in JSON files, not here."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Farm(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    county_code: str | None = None  # e.g. "AB"
    created_at: datetime = Field(default_factory=_now)


class Field_(SQLModel, table=True):
    __tablename__ = "field"

    id: int | None = Field(default=None, primary_key=True)
    farm_id: int = Field(foreign_key="farm.id", index=True)
    name: str
    geometry_geojson: str  # GeoJSON geometry as text (drawn parcel)
    area_ha: float | None = None
    commune_id: str | None = None


class FarmerPriorities(SQLModel, table=True):
    __tablename__ = "farmer_priorities"

    id: int | None = Field(default=None, primary_key=True)
    farm_id: int = Field(foreign_key="farm.id", index=True)
    # Weights 0..1 — yield, water, soil health, risk (challenge req. #6)
    yield_weight: float = 0.25
    water_weight: float = 0.25
    soil_weight: float = 0.25
    risk_weight: float = 0.25


class FieldPlan(SQLModel, table=True):
    """Answers of the 'Plan my field' questions for one field (JSON, see app/planner)."""

    __tablename__ = "field_plan"

    id: int | None = Field(default=None, primary_key=True)
    field_id: int = Field(foreign_key="field.id", index=True, unique=True)
    answers_json: str = "{}"
    updated_at: datetime = Field(default_factory=_now)


class HarvestReport(SQLModel, table=True):
    """What a field actually gave in one season — the data the models learn from.

    source = "history" (entered in the planner for past years) or "report" (after-harvest form)."""

    __tablename__ = "harvest_report"

    id: int | None = Field(default=None, primary_key=True)
    field_id: int = Field(foreign_key="field.id", index=True)
    year: int = Field(index=True)
    crop: str
    yield_t_ha: float | None = None
    maturity: str | None = None  # early / medium / late (maize, sunflower, soy)
    irrigated: bool = False
    problems_json: str = "[]"  # e.g. ["drought", "hail"]
    source: str = "report"
    created_at: datetime = Field(default_factory=_now)
