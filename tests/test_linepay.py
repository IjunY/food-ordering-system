"""LINE Pay (sandbox) as the payment provider, against a fake LINE Pay server."""

import base64
import hashlib
import hmac
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from app.auth.states import UserRole
from app.payments.config import PaymentSettings, get_payment_settings
from app.payments.models import Payment
from app.payments.provider import LinePayProvider, PaymentProviderError
from app.payments.router import get_linepay_provider, get_provider

Headers = Callable[..., dict[str, str]]

CHANNEL_ID = "1234567890"
SECRET = "test-line-pay-channel-secret"
TRANSACTION_ID = "2026112000000000001"  # LINE Pay ids are 19 digits
REFUND_ID = "2026112300000000002"


class FakeLinePay:
    """Records what is sent and answers like LINE Pay's sandbox."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str], dict[str, Any]]] = []
        self.confirm_code = "0000"
        self.request_code = "0000"
        self.refund_code = "0000"

    def __call__(self, url: str, headers: dict[str, str], body: bytes) -> dict:
        self.calls.append((url, headers, json.loads(body)))
        if url.endswith("/v3/payments/request"):
            if self.request_code != "0000":
                return {"returnCode": self.request_code, "returnMessage": "Error"}
            return {
                "returnCode": "0000",
                "returnMessage": "Success.",
                "info": {
                    "paymentUrl": {
                        "web": "https://sandbox-web-pay.line.me/web/payment/wait?x=1",
                        "app": "line://pay/payment/x",
                    },
                    "transactionId": int(TRANSACTION_ID),
                    "paymentAccessToken": "123456789012",
                },
            }
        if url.endswith("/refund"):
            if self.refund_code != "0000":
                return {"returnCode": self.refund_code, "returnMessage": "Error"}
            return {
                "returnCode": "0000",
                "returnMessage": "Success.",
                "info": {
                    "refundTransactionId": int(REFUND_ID),
                    "refundTransactionDate": "2026-11-23T12:00:00Z",
                },
            }
        return {"returnCode": self.confirm_code, "returnMessage": "Done"}

    def paths(self) -> list[str]:
        return [
            url.removeprefix("https://sandbox-api-pay.line.me")
            for url, _, _ in self.calls
        ]


@pytest.fixture
def line_pay(client: TestClient) -> Iterator[FakeLinePay]:
    fake = FakeLinePay()
    settings = PaymentSettings(
        webhook_secret=SecretStr("test-only-webhook-secret-0123456789abcdef"),
        provider="linepay",
        linepay_channel_id=CHANNEL_ID,
        linepay_channel_secret=SecretStr(SECRET),
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )
    provider = LinePayProvider(
        CHANNEL_ID, SECRET, settings.linepay_api_url, "http://testserver/", send=fake
    )
    overrides = client.app.dependency_overrides  # type: ignore[attr-defined]
    overrides[get_payment_settings] = lambda: settings
    overrides[get_provider] = lambda: provider
    overrides[get_linepay_provider] = lambda: provider
    yield fake
    overrides.clear()


@pytest.fixture
def customer(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("990000001")


@pytest.fixture
def order(
    client: TestClient,
    auth_headers: Headers,
    customer: dict[str, str],
    make_vendor: Callable[..., int],
) -> dict:
    """An order of two 80-dollar bentos (160)."""
    vendor_id = make_vendor("Test Bento", "測試便當")
    staff = auth_headers("staff01", UserRole.STAFF, vendor_id=vendor_id)
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
    ).json()
    response = client.post(
        "/api/orders",
        json={"items": [{"item_id": item["id"], "quantity": 2}]},
        headers=customer,
    )
    assert response.status_code == 201, response.text
    return response.json()


def start(client: TestClient, customer: dict[str, str], order_id: int) -> dict:
    response = client.post(
        "/api/payments", json={"order_id": order_id}, headers=customer
    )
    assert response.status_code == 201, response.text
    return response.json()


def trade_no_of(fake: FakeLinePay) -> str:
    return fake.calls[0][2]["orderId"]


def come_back(client: TestClient, trade_no: str, transaction_id: str = TRANSACTION_ID):
    return client.get(
        "/api/payments/linepay/confirm",
        params={"transactionId": transaction_id, "orderId": trade_no},
        follow_redirects=False,
    )


def order_payment(client: TestClient, customer: dict[str, str], order_id: int) -> str:
    return client.get(f"/api/orders/{order_id}", headers=customer).json()[
        "payment_status"
    ]


def test_request_is_signed_the_way_line_pay_expects() -> None:
    fake = FakeLinePay()
    provider = LinePayProvider(
        CHANNEL_ID,
        SECRET,
        "https://sandbox-api-pay.line.me/",
        "http://app.test/",
        send=fake,
    )
    checkout = provider.create_checkout("abc123", 160)

    assert checkout.url.startswith("https://sandbox-web-pay.line.me/")
    assert (
        checkout.provider_ref == TRANSACTION_ID
    )  # kept as text: too long for JS numbers
    url, headers, body = fake.calls[0]
    assert url == "https://sandbox-api-pay.line.me/v3/payments/request"
    assert headers["X-LINE-ChannelId"] == CHANNEL_ID
    # Signature = Base64(HMAC-SHA256(secret, secret + path + body + nonce))
    sent_body = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    message = (
        SECRET
        + "/v3/payments/request"
        + sent_body
        + headers["X-LINE-Authorization-Nonce"]
    )
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    assert headers["X-LINE-Authorization"] == expected
    # The amounts add up the way LINE Pay checks them
    assert body["amount"] == 160 and body["currency"] == "TWD"
    package = body["packages"][0]
    assert package["amount"] == sum(
        p["price"] * p["quantity"] for p in package["products"]
    )
    assert body["orderId"] == "abc123"
    assert body["redirectUrls"] == {
        "confirmUrl": "http://app.test/api/payments/linepay/confirm",
        "cancelUrl": "http://app.test/api/payments/linepay/cancel?trade_no=abc123",
    }

    fake.request_code = "1104"  # e.g. a wrong channel
    with pytest.raises(PaymentProviderError):
        provider.create_checkout("abc124", 160)


def test_a_payment_without_a_line_pay_transaction_has_nothing_to_refund() -> None:
    # Paid on the mock checkout page (no LINE Pay transaction id): LINE Pay holds
    # no money for it, so there is nothing to ask LINE Pay for
    fake = FakeLinePay()
    provider = LinePayProvider(
        CHANNEL_ID,
        SECRET,
        "https://sandbox-api-pay.line.me/",
        "http://app.test/",
        send=fake,
    )

    assert provider.refund(None, 160) is None
    assert fake.calls == []


def test_customer_pays_with_line_pay(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    assert client.get("/api/payments/config").json() == {"provider": "linepay"}
    created = start(client, customer, order["id"])
    assert created["checkout_url"].startswith("https://sandbox-web-pay.line.me/")
    assert order_payment(client, customer, order["id"]) == "pending"

    # Pressing "pay" again reuses the same LINE Pay page (no second request)
    again = start(client, customer, order["id"])
    assert again["payment"]["id"] == created["payment"]["id"]
    assert again["checkout_url"] == created["checkout_url"]
    assert line_pay.paths() == ["/v3/payments/request"]

    # The customer approves on LINE Pay and is sent back: we confirm, then go to the pass
    back = come_back(client, trade_no_of(line_pay))
    assert back.status_code == 303
    assert back.headers["location"] == f"/#paid-{order['id']}"
    assert line_pay.paths()[-1] == f"/v3/payments/{TRANSACTION_ID}/confirm"
    assert line_pay.calls[-1][2] == {"amount": 160, "currency": "TWD"}
    assert order_payment(client, customer, order["id"]) == "paid"

    # Reloading the page confirms nothing twice
    assert (
        come_back(client, trade_no_of(line_pay)).headers["location"]
        == f"/#paid-{order['id']}"
    )
    assert len(line_pay.calls) == 2


def test_a_transaction_id_from_elsewhere_is_refused(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    start(client, customer, order["id"])
    forged = come_back(
        client, trade_no_of(line_pay), transaction_id="2026112099999999999"
    )
    assert forged.status_code == 400
    assert line_pay.paths() == ["/v3/payments/request"]  # never confirmed
    assert order_payment(client, customer, order["id"]) == "pending"


def test_failed_confirm_and_cancel_send_the_customer_back_to_pay(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    start(client, customer, order["id"])
    line_pay.confirm_code = "1141"  # e.g. the payment was not approved
    back = come_back(client, trade_no_of(line_pay))
    assert back.headers["location"] == f"/#pay-{order['id']}"
    assert order_payment(client, customer, order["id"]) == "failed"

    # Trying again starts a new LINE Pay transaction; this time the customer cancels
    retry = start(client, customer, order["id"])
    assert line_pay.paths().count("/v3/payments/request") == 2
    cancel = client.get(
        "/api/payments/linepay/cancel",
        params={"trade_no": line_pay.calls[-1][2]["orderId"]},
        follow_redirects=False,
    )
    assert cancel.status_code == 303
    assert cancel.headers["location"] == f"/#pay-{order['id']}"
    status = client.get(
        f"/api/payments/{retry['payment']['id']}", headers=customer
    ).json()
    assert status["status"] == "failed"


def test_cancelled_orders_are_not_charged(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    start(client, customer, order["id"])
    client.post(f"/api/orders/{order['id']}/cancel", headers=customer)
    back = come_back(client, trade_no_of(line_pay))
    assert back.headers["location"] == f"/#pay-{order['id']}"
    assert "/confirm" not in "".join(
        line_pay.paths()
    )  # LINE Pay was never asked to charge


def _paid(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    start(client, customer, order["id"])
    assert (
        come_back(client, trade_no_of(line_pay)).headers["location"]
        == f"/#paid-{order['id']}"
    )


def _refund_ref(client: TestClient, order_id: int) -> str | None:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        return session.scalar(
            select(Payment.refund_ref).where(Payment.order_id == order_id)
        )


def test_cancelling_a_paid_order_refunds_it_on_line_pay(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    _paid(client, line_pay, customer, order)

    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer)

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert line_pay.paths()[-1] == f"/v3/payments/{TRANSACTION_ID}/refund"
    assert line_pay.calls[-1][2] == {"refundAmount": 160}
    assert order_payment(client, customer, order["id"]) == "refunded"
    assert _refund_ref(client, order["id"]) == REFUND_ID

    # Cancelling again is refused by the order (already cancelled), not sent to LINE Pay
    again = client.post(f"/api/orders/{order['id']}/cancel", headers=customer)
    assert again.status_code == 409
    assert line_pay.paths().count(f"/v3/payments/{TRANSACTION_ID}/refund") == 1


def test_a_failed_refund_leaves_the_order_as_it_was(
    client: TestClient,
    line_pay: FakeLinePay,
    auth_headers: Headers,
    customer: dict[str, str],
    order: dict,
) -> None:
    _paid(client, line_pay, customer, order)
    staff = auth_headers("staff02", UserRole.STAFF, vendor_id=order["vendor_id"])

    line_pay.refund_code = "9000"  # LINE Pay internal error
    rejected = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers=staff,
    )
    assert rejected.status_code == 502
    still = client.get(f"/api/orders/{order['id']}", headers=customer).json()
    assert still["status"] == "confirming"
    assert still["payment_status"] == "paid"

    # LINE Pay did refund it after all, but we never heard back: trying again
    # gets "already refunded" (1165), which completes the cancellation
    line_pay.refund_code = "1165"
    retry = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers=staff,
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "cancelled"
    assert retry.json()["payment_status"] == "refunded"
    assert _refund_ref(client, order["id"]) is None


def test_orders_paid_at_the_counter_are_not_refunded_online(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    client.post(f"/api/orders/{order['id']}/pay-at-pickup", headers=customer)

    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer)

    assert cancelled.status_code == 200, cancelled.text
    assert line_pay.calls == []


def test_line_pay_down_is_reported(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    line_pay.request_code = "9000"
    response = client.post(
        "/api/payments", json={"order_id": order["id"]}, headers=customer
    )
    assert response.status_code == 502
    assert order_payment(client, customer, order["id"]) == "failed"


def test_each_provider_only_answers_its_own_pages(
    client: TestClient, line_pay: FakeLinePay, customer: dict[str, str], order: dict
) -> None:
    # With LINE Pay on, the mock checkout pages are gone
    start(client, customer, order["id"])
    assert (
        client.get(f"/api/payments/mock-checkout/{trade_no_of(line_pay)}").status_code
        == 404
    )

    # ... and with the mock provider, the LINE Pay return pages are gone
    client.app.dependency_overrides.clear()  # type: ignore[attr-defined]
    client.app.dependency_overrides[get_payment_settings] = lambda: PaymentSettings(  # type: ignore[attr-defined]
        webhook_secret=SecretStr("test-only-webhook-secret-0123456789abcdef"),
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )
    assert come_back(client, trade_no_of(line_pay)).status_code == 404


def test_line_pay_needs_its_keys() -> None:
    with pytest.raises(ValidationError):
        PaymentSettings(
            webhook_secret=SecretStr("test-only-webhook-secret-0123456789abcdef"),
            provider="linepay",
            _env_file=None,  # pyright: ignore[reportCallIssue]
        )
