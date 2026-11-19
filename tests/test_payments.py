# 付款模組的測試。
# 跟其他測試一樣用 conftest.py 的 client（真的 PostgreSQL，每個測試結束後自動還原），
# 所以要先啟動資料庫並跑過 `uv run alembic upgrade head`。

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.auth.states import UserRole
from app.payments import repo, service
from app.payments.config import PaymentSettings, get_payment_settings
from app.payments.models import Payment
from app.payments.provider import MockProvider, sign
from app.payments.states import PaymentStatus, can_transition

Headers = Callable[..., dict[str, str]]

SECRET = "test-only-webhook-secret-0123456789abcdef"
provider = MockProvider(SECRET)


# ---------- 共用的準備工作（fixture） ----------


# autouse=True：這個檔案裡每個測試都會自動套用，不用一個一個寫
@pytest.fixture(autouse=True)
def payment_settings(client: TestClient) -> PaymentSettings:
    # 測試不讀 .env：把付款設定換成固定的測試值
    settings = PaymentSettings(
        webhook_secret=SecretStr(SECRET),
        expire_minutes=15,
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )
    client.app.dependency_overrides[get_payment_settings] = lambda: settings  # type: ignore[attr-defined]
    return settings


@pytest.fixture
def vendor_id(make_vendor: Callable[..., int]) -> int:
    return make_vendor("Test Bento", "測試便當")


@pytest.fixture
def staff(auth_headers: Headers, vendor_id: int) -> dict[str, str]:
    # 這家店的店員：店員只能管自己店的菜單和訂單
    return auth_headers("staff01", UserRole.STAFF, vendor_id=vendor_id)


@pytest.fixture
def customer(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("990000001")


@pytest.fixture
def other_customer(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("990000002")


@pytest.fixture
def order(
    client: TestClient,
    staff: dict[str, str],
    customer: dict[str, str],
    vendor_id: int,
) -> dict:
    """一張 customer 下的訂單：兩個 80 元的便當，總共 160 元。"""
    item = client.post(
        "/api/menu-items",
        json={
            "vendor_id": vendor_id,
            "item_name_zh": "雞腿便當",
            "item_name_en": "Chicken Bento",
            "category_zh": "便當",
            "category_en": "Bento",
            "price": 80,
            "prep_minutes": 5,
        },
        headers=staff,
    )
    assert item.status_code == 201, item.text
    response = client.post(
        "/api/orders",
        json={"items": [{"item_id": item.json()["id"], "quantity": 2}]},
        headers=customer,
    )
    assert response.status_code == 201, response.text
    return response.json()


def start(client: TestClient, headers: dict[str, str], order_id: int) -> dict:
    """開始付款，回傳 {"payment": {...}, "checkout_url": "..."}。"""
    response = client.post(
        "/api/payments", json={"order_id": order_id}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def trade_no_of(created: dict) -> str:
    # 付款頁網址的最後一段就是交易編號
    return created["checkout_url"].rsplit("/", 1)[-1]


def send_callback(
    client: TestClient,
    trade_no: str,
    amount: int,
    success: bool = True,
    secret: str = SECRET,
):
    """扮演金流商，送一則通知到 /api/payments/callback。"""
    body, _ = provider.build_callback(trade_no, amount, success)
    return client.post(
        "/api/payments/callback",
        content=body,
        headers={"X-Signature": sign(body, secret)},
    )


def status_of(client: TestClient, headers: dict[str, str], payment_id: int) -> str:
    response = client.get(f"/api/payments/{payment_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["status"]


# ---------- 狀態機 ----------


def test_pending_can_become_paid() -> None:
    assert can_transition(PaymentStatus.PENDING, PaymentStatus.PAID)


def test_finished_payments_cannot_change() -> None:
    assert not can_transition(PaymentStatus.PAID, PaymentStatus.PENDING)
    assert not can_transition(PaymentStatus.FAILED, PaymentStatus.PAID)
    assert not can_transition(PaymentStatus.EXPIRED, PaymentStatus.PAID)


# ---------- 建立付款 ----------


def test_amount_comes_from_the_server(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    # 前端硬塞一個 1 元的價格：後端不理它，金額還是訂單的 160
    response = client.post(
        "/api/payments", json={"order_id": order["id"], "amount": 1}, headers=customer
    )

    assert response.status_code == 201, response.text
    payment = response.json()["payment"]
    assert payment["amount"] == 160
    assert payment["status"] == "pending"
    assert payment["paid_at"] is None


def test_paying_requires_login(client: TestClient, order: dict) -> None:
    response = client.post("/api/payments", json={"order_id": order["id"]})
    assert response.status_code == 401


def test_cannot_pay_someone_elses_order(
    client: TestClient,
    other_customer: dict[str, str],
    staff: dict[str, str],
    order: dict,
) -> None:
    # 別的客人：訂單看起來就像不存在
    response = client.post(
        "/api/payments", json={"order_id": order["id"]}, headers=other_customer
    )
    assert response.status_code == 404

    # 店員看得到訂單，但不能替客人付款
    response = client.post(
        "/api/payments", json={"order_id": order["id"]}, headers=staff
    )
    assert response.status_code == 404


def test_unknown_order_is_404(client: TestClient, customer: dict[str, str]) -> None:
    response = client.post(
        "/api/payments", json={"order_id": 999_999}, headers=customer
    )
    assert response.status_code == 404


def test_cannot_pay_a_cancelled_order(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    client.post(f"/api/orders/{order['id']}/cancel", headers=customer)

    response = client.post(
        "/api/payments", json={"order_id": order["id"]}, headers=customer
    )
    assert response.status_code == 409


def test_clicking_pay_twice_reuses_the_same_payment(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    first = start(client, customer, order["id"])
    second = start(client, customer, order["id"])

    assert first["payment"]["id"] == second["payment"]["id"]
    assert first["checkout_url"] == second["checkout_url"]


# ---------- 金流通知（callback） ----------


def test_valid_callback_marks_the_payment_paid(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])

    response = send_callback(client, trade_no_of(created), 160)

    assert response.status_code == 200
    paid = client.get(f"/api/payments/{created['payment']['id']}", headers=customer)
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_at"] is not None
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        assert service.is_order_paid(session, order["id"])


def test_forged_callback_is_rejected(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])

    # 攻擊者不知道真正的密鑰，簽章對不上
    response = send_callback(
        client, trade_no_of(created), 160, secret="attacker-guessed-secret"
    )

    assert response.status_code == 400
    assert status_of(client, customer, created["payment"]["id"]) == "pending"


def test_callback_without_signature_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/payments/callback",
        content=b'{"trade_no": "x", "amount": 160, "success": true}',
    )
    assert response.status_code == 422


def test_callback_with_wrong_amount_is_rejected(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])

    # 簽章正確，但金流商說只收到 1 元
    response = send_callback(client, trade_no_of(created), 1)

    assert response.status_code == 400
    assert status_of(client, customer, created["payment"]["id"]) == "pending"


def test_duplicate_callbacks_change_nothing(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    payment_id = created["payment"]["id"]
    send_callback(client, trade_no_of(created), 160)
    first = client.get(f"/api/payments/{payment_id}", headers=customer).json()

    # 同一則通知重送，再來一則「失敗」通知：都回 200，但已付款的結果不變
    assert send_callback(client, trade_no_of(created), 160).status_code == 200
    assert send_callback(client, trade_no_of(created), 160, False).status_code == 200

    again = client.get(f"/api/payments/{payment_id}", headers=customer).json()
    assert again["status"] == "paid"
    assert again["paid_at"] == first["paid_at"]


def test_cannot_pay_an_order_twice(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    send_callback(client, trade_no_of(created), 160)

    response = client.post(
        "/api/payments", json={"order_id": order["id"]}, headers=customer
    )
    assert response.status_code == 409


def test_failed_payment_can_be_retried(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    send_callback(client, trade_no_of(created), 160, success=False)
    assert status_of(client, customer, created["payment"]["id"]) == "failed"

    retry = start(client, customer, order["id"])

    assert retry["payment"]["id"] != created["payment"]["id"]
    assert retry["payment"]["status"] == "pending"


def test_order_cancelled_while_paying_is_not_marked_paid(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    client.post(f"/api/orders/{order['id']}/cancel", headers=customer)

    # 訂單已經取消，就算金流商說成功，也不能變成「已取消卻已付款」
    assert send_callback(client, trade_no_of(created), 160).status_code == 200

    assert status_of(client, customer, created["payment"]["id"]) == "failed"


# ---------- 逾時 ----------


def _make_overdue(client: TestClient, payment_id: int) -> None:
    # 直接改資料庫，假裝付款期限在一分鐘前就過了
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        payment = session.get(Payment, payment_id)
        payment.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()


def test_overdue_payment_expires(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    _make_overdue(client, created["payment"]["id"])

    # 過期後才到的「成功」通知不接受
    assert send_callback(client, trade_no_of(created), 160).status_code == 200
    assert status_of(client, customer, created["payment"]["id"]) == "expired"

    # 但可以重新建立一筆新的付款
    retry = start(client, customer, order["id"])
    assert retry["payment"]["id"] != created["payment"]["id"]


# ---------- 查詢付款 ----------


def test_who_can_see_a_payment(
    client: TestClient,
    customer: dict[str, str],
    other_customer: dict[str, str],
    staff: dict[str, str],
    order: dict,
) -> None:
    payment_id = start(client, customer, order["id"])["payment"]["id"]
    url = f"/api/payments/{payment_id}"

    assert client.get(url, headers=customer).status_code == 200
    assert client.get(url, headers=staff).status_code == 200  # 店員要確認客人付了沒
    assert client.get(url, headers=other_customer).status_code == 404
    assert client.get(url).status_code == 401


def test_latest_payment_of_an_order(
    client: TestClient,
    customer: dict[str, str],
    other_customer: dict[str, str],
    order: dict,
) -> None:
    url = f"/api/payments/order/{order['id']}"
    assert client.get(url, headers=customer).status_code == 404  # 還沒開始付款

    first = start(client, customer, order["id"])
    send_callback(client, trade_no_of(first), 160, success=False)
    second = start(client, customer, order["id"])

    latest = client.get(url, headers=customer)
    assert latest.status_code == 200
    assert latest.json()["id"] == second["payment"]["id"]
    assert client.get(url, headers=other_customer).status_code == 404


# ---------- 資料庫的最後防線 ----------


def test_database_refuses_two_active_payments_for_one_order(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    start(client, customer, order["id"])

    # 繞過 service，直接往資料庫塞第二筆待付款：唯一索引會擋下來
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        duplicate = Payment(
            order_id=order["id"],
            amount=160,
            trade_no="duplicate",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        with pytest.raises(IntegrityError):
            repo.add(session, duplicate)


def test_two_simultaneous_pay_requests_end_up_with_one_payment(
    client: TestClient,
    customer: dict[str, str],
    order: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = start(client, customer, order["id"])

    # 模擬「兩個請求同時進來」：讓第二個請求第一次查詢時看不到已經存在的付款，
    # 於是它也去新增，然後撞到唯一索引。service 應該改成回傳原本那一筆
    real = repo.get_active_for_order
    calls = {"n": 0}

    def blind_once(session, order_id):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return None if calls["n"] == 1 else real(session, order_id)

    monkeypatch.setattr(repo, "get_active_for_order", blind_once)

    second = start(client, customer, order["id"])
    assert second["payment"]["id"] == first["payment"]["id"]


# ---------- 假付款頁：走完整個流程 ----------


def test_full_flow_through_the_mock_checkout_page(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    # 1. 開始付款
    created = start(client, customer, order["id"])

    # 2. 打開假付款頁
    page = client.get(created["checkout_url"])
    assert page.status_code == 200
    assert "NT$ 160" in page.text

    # 3. 按下「模擬付款成功」
    done = client.post(
        f"{created['checkout_url']}/complete", params={"success": "true"}
    )
    assert done.status_code == 200

    # 4. 查詢付款狀態
    assert status_of(client, customer, created["payment"]["id"]) == "paid"


def test_mock_checkout_is_hidden_in_production(
    client: TestClient, customer: dict[str, str], order: dict
) -> None:
    created = start(client, customer, order["id"])
    # 把環境切成正式環境：假付款頁要消失，不然任何人都能按「模擬付款成功」
    client.app.state.app_settings = client.app.state.app_settings.model_copy(  # type: ignore[attr-defined]
        update={"app_env": "prod"}
    )

    assert client.get(created["checkout_url"]).status_code == 404
    done = client.post(
        f"{created['checkout_url']}/complete", params={"success": "true"}
    )
    assert done.status_code == 404
    assert status_of(client, customer, created["payment"]["id"]) == "pending"
