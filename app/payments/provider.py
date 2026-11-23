# 金流商的介面，以及兩個金流商：假的（MockProvider）和 LINE Pay（LinePayProvider，先接 sandbox）。
# 用哪一個由 .env 的 PAYMENT_PROVIDER 決定（config.py）。

import base64
import hashlib  # 提供 SHA-256 等雜湊演算法
import hmac  # 用「密鑰 + 內容」算出簽章，用來證明內容沒被竄改、也不是別人偽造的
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Checkout:
    """建立交易的結果：要把使用者導過去的付款頁網址，以及金流商給這筆交易的編號（有的話）。"""

    url: str
    provider_ref: str | None = None


class PaymentProviderError(Exception):
    """金流商回報錯誤，或連不上金流商。"""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        # 金流商的錯誤代碼（例如 LINE Pay 的 returnCode）；連不上時是 None
        self.code = code


class PaymentProvider(Protocol):
    # Protocol 是「規格說明」：只要一個 class 有這三個方法，就能被當成 PaymentProvider 使用。
    # 這裡的 ... 代表「只定義名稱和參數，不寫內容」

    def create_checkout(self, trade_no: str, amount: int) -> Checkout:
        """向金流商建立一筆交易，回傳付款頁網址（和金流商的交易編號）。失敗時丟 PaymentProviderError。"""
        ...

    def verify_callback(self, body: bytes, signature: str) -> bool:
        """檢查一則通知的簽章是否正確。"""
        ...

    def refund(self, provider_ref: str | None, amount: int) -> str | None:
        """把一筆已付款的錢全部退回去，回傳金流商的退款編號（沒有就 None）。

        provider_ref 是付款時金流商給的交易編號。退不了時丟 PaymentProviderError。
        """
        ...


def sign(body: bytes, secret: str) -> str:
    # 用密鑰對內容算出 HMAC-SHA256 簽章，轉成 16 進位字串。
    # 同樣的內容 + 同樣的密鑰，一定算出同樣的簽章；內容改了一個字，簽章就完全不同。
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class MockProvider:
    """假的金流商：不收真的錢，用來開發和示範。"""

    def __init__(self, secret: str) -> None:
        # 前面加底線 _ 是 Python 的慣例，表示「內部使用，外面不要直接碰」
        self._secret = secret

    def create_checkout(self, trade_no: str, amount: int) -> Checkout:
        # 真的金流商會回傳它網站上的付款頁。我們的假付款頁就做在自己的網站上
        # （所有 API 都掛在 /api 底下，所以網址以 /api/payments 開頭）
        return Checkout(url=f"/api/payments/mock-checkout/{trade_no}")

    def verify_callback(self, body: bytes, signature: str) -> bool:
        # 自己用密鑰重算一次簽章，跟通知附上的比對。
        # 一定要用 compare_digest，不要用 ==：
        # == 比到第一個不同的字元就停下來，攻擊者可以從回應快慢一點一點猜出正確簽章；
        # compare_digest 不管哪裡不同，花的時間都一樣。
        expected = sign(body, self._secret)
        # 兩邊都轉成 bytes 再比：簽章裡如果被塞了奇怪的字元，會回傳 False 而不是讓程式出錯
        return hmac.compare_digest(expected.encode(), signature.encode())

    def refund(self, provider_ref: str | None, amount: int) -> str | None:
        # 假付款頁沒有真的收錢，所以也沒有錢要退
        return None

    def build_callback(
        self, trade_no: str, amount: int, success: bool
    ) -> tuple[bytes, str]:
        # 模擬「金流商伺服器」組出一則通知：內容轉成 JSON 位元組，再附上簽章。
        # 真實情況下這段是金流商做的，我們只負責收；這裡是為了假付款頁才需要它。
        body = json.dumps(
            {"trade_no": trade_no, "amount": amount, "success": success}
        ).encode()
        return body, sign(body, self._secret)


# ---------- LINE Pay（Online API v3） ----------
# 流程和假金流商不同：LINE Pay 不會主動通知我們，而是
#   1. 我們呼叫 Request API，拿到付款頁網址和 transactionId
#   2. 使用者在 LINE Pay 付款頁同意付款後，瀏覽器被導回我們的 confirmUrl（帶著 transactionId）
#   3. 我們再呼叫 Confirm API，LINE Pay 回 0000 才算真的扣款成功
# 所以付款成功與否，是「我們的伺服器問 LINE Pay」得到的答案，不是瀏覽器說了算。
# 文件：https://developers-pay.line.me/online-api-v3

# Refund API 的回應代碼：這筆交易已經退款過了
ALREADY_REFUNDED = "1165"

# 送出請求的函式：(網址, 標頭, 內容) -> 回傳的 JSON。測試時換成假的，不用真的連網路
Sender = Callable[[str, dict[str, str], bytes], dict[str, Any]]


def _post_json(url: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result: dict[str, Any] = json.loads(response.read())
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PaymentProviderError(f"Could not reach LINE Pay: {exc}") from exc


class LinePayProvider:
    """LINE Pay。api_url 預設是 sandbox（測試環境），不會真的扣款。"""

    def __init__(
        self,
        channel_id: str,
        channel_secret: str,
        api_url: str,
        app_url: str,
        send: Sender = _post_json,
    ) -> None:
        self._channel_id = channel_id
        self._secret = channel_secret
        self._api_url = api_url.rstrip("/")
        # 我們網站的網址（例如 http://127.0.0.1:8000），用來組出付款後導回來的網址
        self._app_url = app_url.rstrip("/")
        self._send = send

    def _call(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        # LINE Pay 的簽章：Base64(HMAC-SHA256(channel secret, secret + 路徑 + 內容 + nonce))
        # 簽的內容和送出的內容必須一字不差，所以先轉成字串再一起用
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        nonce = str(uuid.uuid4())  # 每次都不一樣，別人錄下來重送也沒用
        message = (self._secret + path + body + nonce).encode()
        signature = base64.b64encode(
            hmac.new(self._secret.encode(), message, hashlib.sha256).digest()
        ).decode()
        headers = {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": self._channel_id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": signature,
        }
        result = self._send(self._api_url + path, headers, body.encode())
        if result.get("returnCode") != "0000":
            raise PaymentProviderError(
                f"LINE Pay error {result.get('returnCode')}: {result.get('returnMessage')}",
                code=result.get("returnCode"),
            )
        return result

    def create_checkout(self, trade_no: str, amount: int) -> Checkout:
        # orderId 用我們的 trade_no；付款後 LINE Pay 會把 transactionId 和 orderId 加在 confirmUrl 後面
        payments = f"{self._app_url}/api/payments/linepay"
        result = self._call(
            "/v3/payments/request",
            {
                "amount": amount,
                "currency": "TWD",
                "orderId": trade_no,
                "packages": [
                    {
                        "id": trade_no,
                        "amount": amount,
                        "name": "NTHU 點餐",
                        "products": [
                            {"name": "NTHU 點餐訂單", "quantity": 1, "price": amount}
                        ],
                    }
                ],
                "redirectUrls": {
                    "confirmUrl": f"{payments}/confirm",
                    "cancelUrl": f"{payments}/cancel?trade_no={trade_no}",
                },
            },
        )
        info = result["info"]
        # transactionId 是 19 位數的整數，存成字串（JavaScript 的數字放不下這麼長）
        return Checkout(
            url=info["paymentUrl"]["web"], provider_ref=str(info["transactionId"])
        )

    def confirm(self, transaction_id: str, amount: int) -> bool:
        """使用者同意付款後，向 LINE Pay 確認扣款。成功回傳 True。"""
        try:
            self._call(
                f"/v3/payments/{transaction_id}/confirm",
                {"amount": amount, "currency": "TWD"},
            )
        except PaymentProviderError:
            return False
        return True

    def refund(self, provider_ref: str | None, amount: int) -> str | None:
        """全額退款（Refund API）。LINE Pay 說「已經退過了」（1165）也算成功：
        上次退款成功、但我們的資料庫沒存到時，再按一次取消就能補上。"""
        if provider_ref is None:
            # 沒有 LINE Pay 交易編號：這筆是在假付款頁付的，LINE Pay 沒收到錢
            return None
        try:
            result = self._call(
                f"/v3/payments/{provider_ref}/refund", {"refundAmount": amount}
            )
        except PaymentProviderError as exc:
            if exc.code == ALREADY_REFUNDED:
                return None
            raise
        # 退款已經成功了：就算回應裡少了退款編號，也不要因此出錯
        ref = result.get("info", {}).get("refundTransactionId")
        return None if ref is None else str(ref)

    def verify_callback(self, body: bytes, signature: str) -> bool:
        # LINE Pay 不送伺服器對伺服器的通知（結果靠 confirm 問），所以這個網址一律拒絕
        return False
