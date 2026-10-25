from fastapi.testclient import TestClient

from app.domain.finance import dscr


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


def reject_open_reviews(client: TestClient, spec_token: str) -> None:
    queue = client.get("/api/specialist/applications", headers=auth(spec_token))
    assert queue.status_code == 200, queue.text
    for item in queue.json():
        rejected = client.post(
            f"/api/specialist/applications/{item['id']}/decision",
            headers=auth(spec_token),
            json={"action": "reject", "reject_reason": "Освобождаем продукт для следующего сценария"},
        )
        assert rejected.status_code == 200, rejected.text


def test_razvitie_queue_and_specialist_offer(client: TestClient):
    spec = login(client, "spec", "spec123")
    reject_open_reviews(client, spec)
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
    spec = login(client, "spec", "spec123")
    reject_open_reviews(client, spec)
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
    assert "product:" not in body["risk_memo"]
    assert "решает специалист" in body["risk_memo"]
    assert any(word in body["risk_memo"] for word in ("высокий", "хороший", "средний", "слабый"))
    assert "good" not in body["risk_memo"]
    egrul_step = next(step for step in body["pipeline"] if step["code"] == "egrul")
    assert egrul_step["detail"] == "действует"
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
    bki = next(factor for factor in dossier["scoring"]["factors"] if factor["code"] == "bki")
    assert bki["points"] == 0
    assert bki["comment"] == "Таймаут БКИ — требуется ручная проверка"
    assert dossier["enrichment"]["bki"]["status"] == "timeout"
    assert dossier["enrichment"]["bki"]["current_debt"] is None
    assert dossier["enrichment"]["bki"]["overdue_days"] is None
    assert dossier["enrichment"]["bki"]["monthly_payment"] is None
    payment = dossier["monthly_payment"]
    assert dossier["dscr"] == dscr(2_500_000, "10.71", payment, 0)
    assert dossier["dscr"] != dscr(2_500_000, "10.71", payment, 18_000)
    assert f"DSCR {dossier['dscr']}" in dossier["risk_memo"]
    assert "платёж БКИ Н/Д" in dossier["risk_memo"]
    assert "платёж БКИ 0" not in dossier["risk_memo"]


def test_dscr_includes_issued_loan_payment(client: TestClient):
    token = login(client, "ip", "ip123")
    spec = login(client, "spec", "spec123")
    first = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 500000, "requested_term_months": 4},
    ).json()
    assert first["status"] == "offer"
    client.post(f"/api/applications/{first['id']}/accept", headers=auth(token))
    signed = client.post(
        f"/api/applications/{first['id']}/sign",
        headers=auth(token),
        json={"code": "123456"},
    )
    assert signed.status_code == 200, signed.text
    issued_payment = signed.json()["monthly_payment"]
    second = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "restock", "product": "kassa", "requested_amount": 400000, "requested_term_months": 4},
    )
    assert second.status_code == 200, second.text
    dossier = client.get(f"/api/specialist/applications/{second.json()['id']}", headers=auth(spec)).json()
    assert dossier["issued_monthly_payment"] == issued_payment
    payment = dossier["monthly_payment"]
    assert dossier["dscr"] == dscr(2_500_000, "10.71", payment, issued_payment + 18_000)
    assert dossier["dscr"] < dscr(2_500_000, "10.71", payment, 18_000)


def test_signing_loan_is_outside_dscr(client: TestClient):
    spec = login(client, "spec", "spec123")
    reject_open_reviews(client, spec)
    token = login(client, "ip", "ip123")
    kassa = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 500000, "requested_term_months": 4},
    ).json()
    accepted = client.post(f"/api/applications/{kassa['id']}/accept", headers=auth(token))
    assert accepted.json()["status"] == "signing"
    review = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "growth", "product": "razvitie", "requested_amount": 3000000, "requested_term_months": 18},
    )
    assert review.status_code == 200, review.text
    dossier = client.get(f"/api/specialist/applications/{review.json()['id']}", headers=auth(spec)).json()
    assert dossier["issued_monthly_payment"] == 0


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
            "profile_note": "Сменили директора и адрес точки",
        },
    ).json()
    assert created["status"] == "in_review"
    assert created["profile_note"] == "Сменили директора и адрес точки"


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
    spec = login(client, "spec", "spec123")
    reject_open_reviews(client, spec)
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


def test_second_open_kassa_is_blocked_until_issue(client: TestClient):
    token = login(client, "ip", "ip123")
    payload = {"purpose": "cash_gap", "product": "kassa", "requested_amount": 500000, "requested_term_months": 4}
    first = client.post("/api/applications", headers=auth(token), json=payload)
    assert first.status_code == 200, first.text
    blocked = client.post("/api/applications", headers=auth(token), json=payload)
    assert blocked.status_code == 409
    assert first.json()["public_number"] in blocked.json()["detail"]
    client.post(f"/api/applications/{first.json()['id']}/accept", headers=auth(token))
    client.post(
        f"/api/applications/{first.json()['id']}/sign",
        headers=auth(token),
        json={"code": "123456"},
    )
    again = client.post("/api/applications", headers=auth(token), json=payload)
    assert again.status_code == 200, again.text


def test_specialist_needs_comment_for_reject_and_extra(client: TestClient):
    spec = login(client, "spec", "spec123")
    item_id = client.get("/api/specialist/applications", headers=auth(spec)).json()[0]["id"]
    missing_extra = client.post(
        f"/api/specialist/applications/{item_id}/decision",
        headers=auth(spec),
        json={"action": "extra_request", "extra_comment": "   "},
    )
    assert missing_extra.status_code == 400
    missing_reject = client.post(
        f"/api/specialist/applications/{item_id}/decision",
        headers=auth(spec),
        json={"action": "reject", "reject_reason": ""},
    )
    assert missing_reject.status_code == 400
    accepted = client.post(
        f"/api/specialist/applications/{item_id}/decision",
        headers=auth(spec),
        json={"action": "extra_request", "extra_comment": "Уточните модель печи"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["extra_comment"] == "Уточните модель печи"


def test_counteroffer_rejects_unchanged_terms(client: TestClient):
    spec = login(client, "spec", "spec123")
    item = client.get("/api/specialist/applications", headers=auth(spec)).json()[0]
    same = client.post(
        f"/api/specialist/applications/{item['id']}/decision",
        headers=auth(spec),
        json={
            "action": "counteroffer",
            "amount": item["requested_amount"],
            "term_months": item["requested_term_months"],
            "rate_annual": item["offer_rate"] or 25.5,
        },
    )
    assert same.status_code == 400
    assert "Для встречки" in same.json()["detail"]
    changed = client.post(
        f"/api/specialist/applications/{item['id']}/decision",
        headers=auth(spec),
        json={
            "action": "counteroffer",
            "amount": item["requested_amount"] - 10_000,
            "term_months": item["requested_term_months"],
            "rate_annual": item["offer_rate"] or 25.5,
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "counteroffer"
    assert changed.json()["offer_amount"] == item["requested_amount"] - 10_000


def test_other_bank_statement_moves_score_and_dscr(client: TestClient):
    token = login(client, "ip", "ip123")
    spec = login(client, "spec", "spec123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "restock", "product": "kassa", "requested_amount": 2250000, "requested_term_months": 6},
    ).json()
    before = client.get(f"/api/specialist/applications/{created['id']}", headers=auth(spec)).json()
    updated = client.post(
        f"/api/applications/{created['id']}/what-if",
        headers=auth(token),
        json={"action": "other_bank"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "offer"
    assert updated.json()["offer_amount"] == 2_250_000
    after = client.get(f"/api/specialist/applications/{created['id']}", headers=auth(spec)).json()
    assert after["extra_turnover"] > 0
    assert after["scoring"]["total"] != before["scoring"]["total"]
    assert after["dscr"] != before["dscr"]
    assert "из другого банка" in after["risk_memo"]
    assert "good" not in after["risk_memo"]


def test_statement_after_tax_cure_does_not_keep_tax_text(client: TestClient):
    token = login(client, "ooo", "ooo123")
    spec = login(client, "spec", "spec123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 2000000, "requested_term_months": 6},
    ).json()
    assert created["status"] == "rejected"
    cured = client.post(f"/api/applications/{created['id']}/cure", headers=auth(token))
    assert cured.status_code == 200, cured.text
    assert cured.json()["status"] == "in_review"
    offered = client.post(
        f"/api/specialist/applications/{created['id']}/decision",
        headers=auth(spec),
        json={"action": "counteroffer", "amount": 1500000, "term_months": 6, "rate_annual": 22},
    )
    assert offered.status_code == 200, offered.text
    updated = client.post(
        f"/api/applications/{created['id']}/what-if",
        headers=auth(token),
        json={"action": "other_bank"},
    )
    assert updated.status_code == 200, updated.text
    dossier = client.get(f"/api/specialist/applications/{created['id']}", headers=auth(spec)).json()
    assert "Недоимка ФНС снята" not in dossier["risk_memo"]
    assert "из другого банка" in dossier["risk_memo"]


def test_queue_stats_count_live_applications(client: TestClient):
    spec = login(client, "spec", "spec123")
    before = client.get("/api/specialist/stats", headers=auth(spec)).json()
    assert before["queue_size"] >= 1
    assert before["manual_count"] >= 1
    token = login(client, "ip", "ip123")
    created = client.post(
        "/api/applications",
        headers=auth(token),
        json={"purpose": "cash_gap", "product": "kassa", "requested_amount": 500000, "requested_term_months": 4},
    )
    assert created.status_code == 200, created.text
    after = client.get("/api/specialist/stats", headers=auth(spec)).json()
    assert after["auto_count"] == before["auto_count"] + 1
    assert after["auto_share"] is not None
