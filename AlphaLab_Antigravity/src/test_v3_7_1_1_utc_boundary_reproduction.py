from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import inspect

import numpy as np

import export_v3_7_1_1_mt5_canonical_gold_m30_v2 as v2


class FakeMT5:
    TIMEFRAME_M30 = 30
    def __init__(self):
        self.calls = []
    def symbol_select(self, symbol, visible):
        return True
    def copy_rates_range(self, symbol, timeframe, date_from, date_to):
        self.calls.append((symbol, timeframe, date_from, date_to))
        dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"), ("spread", "i8"), ("real_volume", "i8")]
        return np.array([(int(date_from), 1, 1, 1, 1, 1, 1, 1), (int(date_to), 1, 1, 1, 1, 1, 1, 1)], dtype=dtype)
    def last_error(self):
        return (0, "OK")


def test_request_boundaries_are_epoch_integers():
    fake = FakeMT5()
    old = v2.v371.mt5
    v2.v371.mt5 = fake
    try:
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2020, 1, 2, tzinfo=timezone.utc)
        v2._fetch_rates_range_epoch("GOLD", start, end)
    finally:
        v2.v371.mt5 = old
    assert fake.calls
    for _, _, a, b in fake.calls:
        assert isinstance(a, int)
        assert isinstance(b, int)
        assert a == int(start.timestamp())
        assert b == int(end.timestamp())


def test_naive_boundary_is_rejected():
    fake = FakeMT5()
    old = v2.v371.mt5
    v2.v371.mt5 = fake
    try:
        try:
            v2._fetch_rates_range_epoch("GOLD", datetime(2020, 1, 1), datetime(2020, 1, 2, tzinfo=timezone.utc))
            raise AssertionError("naive boundary must fail")
        except ValueError:
            pass
    finally:
        v2.v371.mt5 = old


def test_fetcher_source_contains_no_tzinfo_stripping():
    src = inspect.getsource(v2._fetch_rates_range_epoch)
    assert "replace(tzinfo=None)" not in src
    assert "timestamp()" in src


def test_v2_paths_do_not_overwrite_v371():
    assert v2.CSV_PATH.name == "GOLD_M30_CANONICAL_V2.csv"
    assert v2.SIDECAR_PATH.name == "GOLD_M30_CANONICAL_V2.source.json"
    assert v2.MANIFEST_PATH.name == "GOLD_M30_CANONICAL_V2.manifest.json"
    assert v2.CSV_PATH != v2.V371_CSV


def test_prior_v371_hash_is_frozen():
    assert v2.V371_FROZEN_SHA == "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"


def test_request_start_remains_aware_utc():
    assert v2.v371.REQUEST_START_UTC.tzinfo is not None
    assert int(v2.v371.REQUEST_START_UTC.utcoffset().total_seconds()) == 0


def test_reproduction_does_not_define_strategy_logic():
    names = set(v2.run_reproduction.__code__.co_names)
    assert "run_strategy" not in names
    assert "signal" not in names


def test_chunk_boundary_dedupe_by_raw_epoch():
    fake = FakeMT5()
    old = v2.v371.mt5
    v2.v371.mt5 = fake
    try:
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2022, 1, 2, tzinfo=timezone.utc)
        rates = v2._fetch_rates_range_epoch("GOLD", start, end)
    finally:
        v2.v371.mt5 = old
    times = rates["time"]
    assert len(times) == len(np.unique(times))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.7.1.1 tests passed")
