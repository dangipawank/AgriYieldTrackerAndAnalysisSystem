from services import yield_service


def test_get_trend_data_shape(monkeypatch):
    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return [
                {"year": 2021, "production": 10.0},
                {"year": 2022, "production": 15.5},
            ]

    class FakeConn:
        def execute(self, _query):
            return FakeResult()

    class FakeCtx:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def connect(self):
            return FakeCtx()

    monkeypatch.setattr(yield_service, "engine", FakeEngine())
    data = yield_service.get_trend_data(1)

    assert data["years"] == [2021, 2022]
    assert data["production"] == [10.0, 15.5]


def test_get_crop_comparison_shape(monkeypatch):
    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return [
                {"crop_name": "Rice", "production": 30},
                {"crop_name": "Maize", "production": 20},
            ]

    class FakeConn:
        def execute(self, _query):
            return FakeResult()

    class FakeCtx:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def connect(self):
            return FakeCtx()

    monkeypatch.setattr(yield_service, "engine", FakeEngine())
    data = yield_service.get_crop_comparison()

    assert data["crops"] == ["Rice", "Maize"]
    assert data["production"] == [30.0, 20.0]


def test_get_analysis_summary_keys(monkeypatch):
    call_index = {"n": 0}

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self

        def all(self):
            return self._rows

    class FakeConn:
        def execute(self, _query):
            call_index["n"] += 1
            if call_index["n"] == 1:
                return FakeResult([{"year": 2023, "total_production": 100}])
            if call_index["n"] == 2:
                return FakeResult([
                    {
                        "crop": "Rice",
                        "total_production": 100,
                        "avg_yield_per_hectare": 2.5,
                        "total_area": 40,
                    }
                ])
            return FakeResult([
                {
                    "district_id": 1,
                    "total_production": 100,
                    "avg_yield_per_hectare": 2.5,
                    "total_area": 40,
                }
            ])

    class FakeCtx:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def connect(self):
            return FakeCtx()

    monkeypatch.setattr(yield_service, "engine", FakeEngine())
    summary = yield_service.get_analysis_summary()

    assert set(summary.keys()) == {"by_year", "by_crop", "by_district"}
    assert summary["by_year"][0]["year"] == 2023
