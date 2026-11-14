"""Place search: Nominatim answer -> deduplicated results with the commune holding each point (no network)."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers import geocode as G


class FakeResp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_search_dedupes_and_finds_commune(monkeypatch):
    seg = {"lat": "46.3105", "lon": "23.7210", "name": "Strada Transilvaniei", "type": "residential",
           "boundingbox": ["46.31", "46.311", "23.72", "23.722"], "address": {"town": "Aiud", "county": "Alba"}}
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append((params, headers))
        return FakeResp([seg, dict(seg), {**seg, "lat": "47.9", "lon": "26.5", "name": "Far away", "address": {}}])

    monkeypatch.setattr(G.httpx, "get", fake_get)
    monkeypatch.setattr(G, "limiter", G.RateLimiter(100, 100, 0))
    G._cache.clear()
    c = TestClient(app)
    r = c.get("/api/geocode", params={"q": "Strada Transilvaniei Aiud"})
    assert r.status_code == 200
    res = r.json()["results"]
    assert [x["name"] for x in res] == ["Strada Transilvaniei", "Far away"]
    assert res[0]["commune"]["county"] == "AB" and res[1]["commune"] is None
    params, headers = calls[0]
    assert params["bounded"] == 1 and params["countrycodes"] == "ro" and "SPACE2FEED" in headers["User-Agent"]
    c.get("/api/geocode", params={"q": "strada transilvaniei aiud"})
    assert len(calls) == 1  # cached
    assert c.get("/api/geocode", params={"q": "x"}).status_code == 422
