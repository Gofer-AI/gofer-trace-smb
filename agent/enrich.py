"""Load-bearing Bright Data price enrichment with conference-proof cache."""
from __future__ import annotations

import json
import os
from pathlib import Path

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _normalize(payload: object) -> dict[str, float]:
    if isinstance(payload, list):
        payload = payload[0]
    if not isinstance(payload, dict):
        raise ValueError("Unexpected Bright Data response")
    prices = payload.get("prices", payload)
    return {str(name).casefold(): float(price) for name, price in prices.items() if isinstance(price, (int, float))}


def current_prices(product: str, cache_path: str | Path = "cache/weekly-reorder-fallback.json") -> tuple[dict[str, float], str]:
    cache = Path(cache_path)
    try:
        if os.getenv("GOFER_OFFLINE") == "1":
            raise ConnectionError("offline mode")
        token, dataset = os.environ["BRIGHTDATA_API_KEY"], os.environ["BRIGHTDATA_DATASET_ID"]
        url = "https://api.brightdata.com/datasets/v3/trigger?" + urlencode(
            {"dataset_id": dataset, "include_errors": "true"}
        )
        request = Request(url, data=json.dumps([{"keyword": product}]).encode(), headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        }, method="POST")
        with urlopen(request, timeout=15) as response:
            prices = _normalize(json.load(response))
        if not prices:
            raise ValueError("Bright Data returned no usable prices")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"product": product, "prices": prices}, indent=2), encoding="utf-8")
        return prices, "Bright Data live"
    except (KeyError, HTTPError, URLError, TimeoutError, ValueError, ConnectionError):
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if payload.get("product") != product:
            raise ValueError("Pricing cache does not match requested product")
        return _normalize(payload), "disk cache"
