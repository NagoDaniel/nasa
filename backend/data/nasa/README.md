# NASA data (JSON, not DB)

Each dataset is one file `data/nasa/<dataset>.json`, loaded once into memory by
`app/json_store.py` and served by `GET /api/nasa/<dataset>[?unit=<id>]`.

```json
{
  "source": "NASA POWER (power.larc.nasa.gov)",
  "variable": "T2M_MAX",
  "unit": "°C",
  "period": {"start": "2019-01-01", "end": "2025-12-31", "step": "month"},
  "units": {
    "AB":        {"2019-01": 2.1, "2019-02": 4.3},
    "AB-1026":   {"2019-01": 1.8}
  }
}
```

`units` keys are area ids matching the geo layers: county `code` (e.g. `AB`)
or commune `id` from `communes.geojson.json`. Always fill `source` — every
result in the app must show where its data came from.
