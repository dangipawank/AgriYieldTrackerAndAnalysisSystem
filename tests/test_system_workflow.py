from app import create_app


def test_login_add_report_export_workflow(monkeypatch):
    app = create_app()
    app.testing = True

    import auth_routes
    import routes

    monkeypatch.setattr(auth_routes, "get_user_by_login", lambda _value: {
        "id": 99,
        "username": "farmer1",
        "role": "Farmer",
        "password_hash": "dummy-hash",
    })
    monkeypatch.setattr(auth_routes, "verify_password", lambda _pwd, _hash: True)
    monkeypatch.setattr(auth_routes, "update_user_last_seen", lambda _uid: None)

    class FakeMappingsResult:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self

        def all(self):
            return self._rows

    class FakeScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar(self):
            return self._value

    class FakeScalarsResult:
        def __init__(self, values):
            self._values = values

        def scalars(self):
            return self

        def all(self):
            return self._values

    class FakeConn:
        def execute(self, query, *_args, **_kwargs):
            query_text = str(query)
            if "COUNT(yielddata.yieldid)" in query_text:
                return FakeScalarResult(1)
            if "SUM(yielddata.production)" in query_text:
                return FakeScalarResult(10)
            if "SUM(yielddata.areaharvested)" in query_text:
                return FakeScalarResult(5)
            if "MAX(yielddata.year)" in query_text:
                return FakeScalarResult(2024)
            if "DISTINCT vw_yield_full_report.year" in query_text:
                return FakeScalarsResult([2024])
            return FakeMappingsResult([])

        def commit(self):
            return None

    class FakeCtx:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def connect(self):
            return FakeCtx()

    monkeypatch.setattr(routes, "engine", FakeEngine())

    with app.test_client() as client:
        login_page = client.get("/login")
        assert login_page.status_code == 200

        with client.session_transaction() as sess:
            csrf = sess.get("csrf_token")

        login_response = client.post(
            "/login",
            data={"login": "farmer1", "password": "pw", "csrf_token": csrf},
            follow_redirects=False,
        )
        assert login_response.status_code in (302, 303)

        with client.session_transaction() as sess:
            sess["role"] = "Farmer"

        add_page = client.get("/yield/add")
        assert add_page.status_code == 200

        report_page = client.get("/yield/full_report")
        assert report_page.status_code == 200

        export_csv = client.get("/yield/full_report/export/csv")
        assert export_csv.status_code in (200, 302)
