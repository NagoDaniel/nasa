from typing import Any

from fastapi import APIRouter, HTTPException

from ..json_store import store

router = APIRouter(prefix="/nasa", tags=["nasa"])


@router.get("")
def list_datasets() -> list[str]:
    return store.list("nasa")


@router.get("/{dataset}")
def get_dataset(dataset: str, unit: str | None = None) -> Any:
    """Return a NASA dataset (see data/nasa/README.md), optionally for one area unit."""
    try:
        data = store.get(f"nasa/{dataset}.json")
    except FileNotFoundError:
        raise HTTPException(404, f"Dataset '{dataset}' not found")
    if unit is None:
        return data
    series = data.get("units", {}).get(unit)
    if series is None:
        raise HTTPException(404, f"No data for unit '{unit}' in '{dataset}'")
    return {k: v for k, v in data.items() if k != "units"} | {"unit": unit, "series": series}


@router.get("/crops/{direction}", tags=["crops"])
def get_crops(direction: str) -> Any:
    try:
        return store.get(f"crops/{direction}.json")
    except FileNotFoundError:
        raise HTTPException(404, f"Crop set '{direction}' not found")
