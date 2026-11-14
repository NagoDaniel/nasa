from fastapi import APIRouter, HTTPException, Response

from ..json_store import store

router = APIRouter(prefix="/geo", tags=["geo"])

LAYERS = {"counties", "regions", "communes", "outline", "mask", "labels"}


@router.get("")
def list_layers() -> list[str]:
    return sorted(LAYERS)


@router.get("/{layer}")
def get_layer(layer: str) -> Response:
    if layer not in LAYERS:
        raise HTTPException(404, f"Unknown layer '{layer}'")
    try:
        body = store.raw(f"geo/{layer}.geojson.json")
    except FileNotFoundError:
        raise HTTPException(404, f"Layer '{layer}' not built — run scripts/build_boundaries.py")
    return Response(
        body,
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )
