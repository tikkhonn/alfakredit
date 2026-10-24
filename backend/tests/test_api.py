from fastapi.testclient import TestClient


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"login": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient):
    assert client.get("/api/health").json()["status"] == "ok"


def test_ip_kassa_happy_path_to_issue(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "cash_gap",
            "product": "kassa",
            "requested_amount": 800000,
            "requested_term_months": 6,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "offer"
    assert body["offer_amount"] == 800000
    assert body["scoring"] is None
    assert len(body["pipeline"]) == 6
    assert body["monthly_payment"] and body["monthly_payment"] > 0

    accepted = client.post(f"/api/applications/{body['id']}/accept", headers=auth(token))
    assert accepted.json()["status"] == "signing"

    signed = client.post(
        f"/api/applications/{body['id']}/sign",
        headers=auth(token),
        json={"code": "123456"},
    )
    assert signed.json()["status"] == "issued"


def test_ip_kassa_over_limit_counteroffer(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "restock",
            "product": "kassa",
            "requested_amount": 8000000,
            "requested_term_months": 6,
        },
    )
    body = created.json()
    assert body["status"] == "counteroffer"
    assert body["offer_amount"] == 1_250_000


def test_ooo_stop_factor_reject(client: TestClient):
    token = login(client, "ooo", "ooo123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "cash_gap",
            "product": "kassa",
            "requested_amount": 400000,
            "requested_term_months": 3,
        },
    )
    body = created.json()
    assert body["status"] == "rejected"
    assert "налог" in (body["client_message"] or "").lower()


def test_razvitie_queue_and_specialist_offer(client: TestClient):
    ip_token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(ip_token),
        json={
            "purpose": "growth",
            "product": "razvitie",
            "requested_amount": 4000000,
            "requested_term_months": 24,
            "purpose_details": "Печь и холодильная витрина для второй точки",
        },
    )
    assert created.json()["status"] == "in_review"
    application_id = created.json()["id"]

    spec = login(client, "spec", "spec123")
    queue = client.get("/api/specialist/applications", headers=auth(spec))
    assert any(item["id"] == application_id for item in queue.json())

    dossier = client.get(f"/api/specialist/applications/{application_id}", headers=auth(spec))
    assert dossier.json()["scoring"]["total"] > 0
    assert dossier.json()["policy"]["rules"]

    decided = client.post(
        f"/api/specialist/applications/{application_id}/decision",
        headers=auth(spec),
        json={"action": "offer", "amount": 4000000, "term_months": 24, "rate_annual": 25.5},
    )
    assert decided.json()["status"] == "offer"


def test_specialist_extra_request_same_application(client: TestClient):
    ip_token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(ip_token),
        json={
            "purpose": "growth",
            "product": "razvitie",
            "requested_amount": 3000000,
            "requested_term_months": 18,
            "purpose_details": "Оборудование",
        },
    )
    application_id = created.json()["id"]
    spec = login(client, "spec", "spec123")
    extra = client.post(
        f"/api/specialist/applications/{application_id}/decision",
        headers=auth(spec),
        json={
            "action": "extra_request",
            "extra_fields": ["purpose_details"],
            "extra_comment": "Какая именно печь и сколько стоит",
        },
    )
    assert extra.json()["status"] == "extra_requested"
    same_id = extra.json()["id"]

    filled = client.post(
        f"/api/applications/{same_id}/extra",
        headers=auth(ip_token),
        json={"purpose_details": "Ротационная печь MIWE 4.2 млн, поставка в ноябре"},
    )
    assert filled.json()["id"] == same_id
    assert filled.json()["status"] == "in_review"


def test_client_cannot_see_scoring(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "cash_gap",
            "product": "kassa",
            "requested_amount": 500000,
            "requested_term_months": 4,
        },
    )
    assert created.json()["scoring"] is None
    assert created.json()["policy"] is None


def test_wrong_sign_code(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "cash_gap",
            "product": "kassa",
            "requested_amount": 500000,
            "requested_term_months": 4,
        },
    )
    application_id = created.json()["id"]
    client.post(f"/api/applications/{application_id}/accept", headers=auth(token))
    failed = client.post(
        f"/api/applications/{application_id}/sign",
        headers=auth(token),
        json={"code": "000000"},
    )
    assert failed.status_code == 400


def test_demo_queue_is_seeded(client: TestClient):
    spec = login(client, "spec", "spec123")
    queue = client.get("/api/specialist/applications", headers=auth(spec))
    assert queue.status_code == 200
    assert len(queue.json()) >= 1
    first = queue.json()[0]
    assert first["status"] == "in_review"
    assert first["purpose_details"]
    dossier = client.get(f"/api/specialist/applications/{first['id']}", headers=auth(spec))
    body = dossier.json()
    assert body["company"]["inn"]
    assert body["company"]["okved"]
    assert body["risk_memo"]
    assert body["dscr"] is not None
    assert 65 <= body["scoring"]["total"] <= 75


def test_issued_kassa_reduces_available_limit(client: TestClient):
    token = login(client, "ip", "ip123")
    before = client.get("/api/me", headers=auth(token)).json()["company"]["kassa_limit"]
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 800000, "requested_term_months": 6},
    ).json()
    client.post(f"/api/applications/{created['id']}/accept", headers=auth(token))
    client.post(f"/api/applications/{created['id']}/sign", headers=auth(token), json={"code": "123456"})
    after = client.get("/api/me", headers=auth(token)).json()["company"]["kassa_limit"]
    assert after == before - 800000


def test_recommend_rounds_suggested_amount(client: TestClient):
    token = login(client, "ip", "ip123")
    rec = client.post("/api/recommend", headers=auth(token), json={"purpose": "cash_gap"}).json()
    assert rec["suggested_amount"] % 10_000 == 0
    assert rec["monthly_payment"] > 0


def test_fns_cure_reopens_same_application(client: TestClient):
    token = login(client, "ooo", "ooo123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 400000, "requested_term_months": 3},
    ).json()
    assert created["status"] == "rejected"
    assert "cure" in created["available_actions"]
    cured = client.post(f"/api/applications/{created['id']}/cure", headers=auth(token))
    assert cured.status_code == 200, cured.text
    body = cured.json()
    assert body["id"] == created["id"]
    assert body["status"] == "in_review"


def test_bki_chaos_fallback_to_specialist(client: TestClient):
    token = login(client, "ip", "ip123")
    spec = login(client, "spec", "spec123")
    client.post("/api/demo/chaos", headers=auth(spec), json={"bki_down": True})
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 500000, "requested_term_months": 4},
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "in_review"
    bki_step = next(step for step in created.json()["pipeline"] if step["code"] == "bki")
    assert bki_step["status"] == "timeout"
    dossier = client.get(
        f"/api/specialist/applications/{created.json()['id']}",
        headers=auth(spec),
    ).json()
    assert "fallback:bki_timeout" in dossier["policy"]["rules"]


def test_what_if_other_bank_covers_request(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "restock", "product": "kassa", "requested_amount": 2250000, "requested_term_months": 6},
    ).json()
    assert created["status"] == "counteroffer"
    assert "what_if" in created["available_actions"]
    updated = client.post(
        f"/api/applications/{created['id']}/what-if",
        headers=auth(token),
        json={"action": "other_bank"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["id"] == created["id"]
    assert body["status"] == "offer"
    assert body["offer_amount"] == 2_250_000


def test_profile_changed_goes_to_specialist(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={
            "purpose": "cash_gap",
            "product": "kassa",
            "requested_amount": 500000,
            "requested_term_months": 4,
            "profile_changed": True,
        },
    ).json()
    assert created["status"] == "in_review"


def test_what_if_msp_collateral_goes_to_specialist(client: TestClient):
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "restock", "product": "kassa", "requested_amount": 2250000, "requested_term_months": 6},
    ).json()
    updated = client.post(
        f"/api/applications/{created['id']}/what-if",
        headers=auth(token),
        json={"action": "msp_collateral"},
    ).json()
    assert updated["status"] == "in_review"
    assert updated["collateral_msp"] is True


def test_created_application_keeps_purpose_after_extra(client: TestClient):
    ip_token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(ip_token),
        json={
            "purpose": "growth",
            "product": "razvitie",
            "requested_amount": 3000000,
            "requested_term_months": 18,
            "purpose_details": "Ротационная печь",
        },
    ).json()
    spec = login(client, "spec", "spec123")
    client.post(
        f"/api/specialist/applications/{created['id']}/decision",
        headers=auth(spec),
        json={"action": "extra_request", "extra_fields": ["purpose_details"], "extra_comment": "Уточните модель"},
    )
    filled = client.post(
        f"/api/applications/{created['id']}/extra",
        headers=auth(ip_token),
        json={"purpose_details": "Ротационная печь MIWE, поставка в ноябре"},
    ).json()
    assert filled["purpose_details"] == "Ротационная печь MIWE, поставка в ноябре"
