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
