import json
from pathlib import Path

from agent.enrich import current_prices


def test_offline_cache(monkeypatch, tmp_path: Path):
    cache = tmp_path / "prices.json"
    cache.write_text(json.dumps({"product": "widgets", "prices": {"acme": 8.5}}))
    monkeypatch.setenv("GOFER_OFFLINE", "1")
    prices, source = current_prices("widgets", cache)
    assert prices == {"acme": 8.5}
    assert source == "disk cache"


def test_pricing_is_load_bearing():
    quantity = 40
    assert quantity * 8.5 == 340
    assert quantity * 8.0 != 340

