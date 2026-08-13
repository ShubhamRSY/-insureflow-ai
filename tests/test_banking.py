"""Balance prediction, transaction categorization, ACH pull dates."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.banking.engine import BankingEngine, categorize_transactions, next_ach_pull_dates, predict_balance
from insureflow.banking.models import AchSchedule, BankTransaction

client = TestClient(app)


def _headers(role: Role = Role.VIEWER, org_id: str = "acme") -> dict[str, str]:
    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
    token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


def test_categorize_payroll_rent_ach() -> None:
    txns = [
        BankTransaction(txn_id="1", amount=4200, posted_on="2026-01-15", description="ADP PAYROLL DIRECT DEP"),
        BankTransaction(txn_id="2", amount=-2200, posted_on="2026-01-01", description="RENT ACME APARTMENTS"),
        BankTransaction(txn_id="3", amount=-95, posted_on="2026-01-03", description="ACH DEBIT GEICO PREMIUM"),
        BankTransaction(txn_id="4", amount=-12.5, posted_on="2026-01-04", description="COFFEE SHOP", mcc="5812"),
    ]
    rows = categorize_transactions(txns)
    by_id = {r.txn_id: r for r in rows}
    assert by_id["1"].category == "payroll"
    assert by_id["2"].category == "rent"
    assert by_id["3"].category in {"insurance", "ach_pull"}
    assert by_id["3"].ach is True
    assert by_id["4"].category == "dining"


def test_monthly_and_semimonthly_ach_dates() -> None:
    monthly = next_ach_pull_dates(AchSchedule(name="premium", cadence="monthly", start_on="2026-01-31", amount=500, count=3))
    assert [d["date"] for d in monthly] == ["2026-01-31", "2026-02-28", "2026-03-31"]

    semi = next_ach_pull_dates(AchSchedule(name="draw", cadence="semimonthly", start_on="2026-01-01", amount=200, count=4))
    assert [d["date"] for d in semi] == ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-15"]

    weekly = next_ach_pull_dates(AchSchedule(name="payroll", cadence="weekly", start_on="2026-01-05", weekday=0, count=2))
    assert weekly[0]["date"] == "2026-01-05"  # Monday
    assert weekly[1]["date"] == "2026-01-12"


def test_balance_forecast_overdraft_with_ach() -> None:
    txns = [
        BankTransaction(txn_id="a", amount=1000, posted_on="2026-03-01", description="deposit"),
        BankTransaction(txn_id="b", amount=-200, posted_on="2026-03-05", description="rent"),
        BankTransaction(txn_id="c", amount=-100, posted_on="2026-03-10", description="utilities"),
    ]
    forecast = predict_balance(
        txns,
        starting_balance=0,
        as_of="2026-03-10",
        horizon_days=20,
        upcoming_ach=[AchSchedule(name="premium", cadence="monthly", start_on="2026-03-15", amount=900, count=1)],
    )
    assert forecast.method == "linear_trend+ach"
    assert forecast.overdraft_risk is True
    assert forecast.min_predicted_balance < 0
    pull_days = [p for p in forecast.predicted if p["ach_pull"]]
    assert pull_days and pull_days[0]["date"] == "2026-03-15"


def test_banking_engine_facade() -> None:
    engine = BankingEngine()
    txns = [BankTransaction(txn_id="1", amount=-40, posted_on="2026-01-02", description="SHELL OIL")]
    assert engine.categorize(txns)[0].category == "fuel"
    dates = engine.ach_dates(AchSchedule(start_on="2026-01-01", cadence="biweekly", count=2))
    assert len(dates) == 2
    pred = engine.predict(txns, starting_balance=500, as_of="2026-01-02", horizon_days=5)
    assert len(pred.predicted) == 5


def test_banking_api() -> None:
    h = _headers()
    cat = client.post(
        "/banking/transactions/categorize",
        headers=h,
        json={"transactions": [{"txn_id": "1", "amount": -50, "posted_on": "2026-01-02", "description": "NETFLIX"}]},
    )
    assert cat.status_code == 200
    assert cat.json()["transactions"][0]["category"] == "subscription"

    ach = client.post(
        "/banking/ach/pull-dates",
        headers=h,
        json={"schedule": {"name": "premium", "cadence": "monthly", "start_on": "2026-06-01", "amount": 120, "count": 2}},
    )
    assert ach.status_code == 200
    assert ach.json()["dates"][1]["date"] == "2026-07-01"

    bal = client.post(
        "/banking/balance/predict",
        headers=h,
        json={
            "transactions": [{"txn_id": "1", "amount": 200, "posted_on": "2026-06-01", "description": "deposit"}],
            "starting_balance": 100,
            "as_of": "2026-06-01",
            "horizon_days": 7,
        },
    )
    assert bal.status_code == 200
    assert len(bal.json()["predicted"]) == 7
