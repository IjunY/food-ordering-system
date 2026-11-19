# 金流商的介面，以及一個假的金流商（MockProvider）。
# 之後要換成綠界、LINE Pay，只要新寫一個 class 實作同樣的方法，其他檔案都不用改。

import hashlib  # 提供 SHA-256 等雜湊演算法
import hmac  # 用「密鑰 + 內容」算出簽章，用來證明內容沒被竄改、也不是別人偽造的
import json
from typing import Protocol


class PaymentProvider(Protocol):
    # Protocol 是「規格說明」：只要一個 class 有這兩個方法，就能被當成 PaymentProvider 使用。
    # 這裡的 ... 代表「只定義名稱和參數，不寫內容」

    def create_checkout(self, trade_no: str, amount: int) -> str:
        """向金流商建立一筆交易，回傳要把使用者導過去的付款頁網址。"""
        ...

    def verify_callback(self, body: bytes, signature: str) -> bool:
        """檢查一則通知的簽章是否正確。"""
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

    def create_checkout(self, trade_no: str, amount: int) -> str:
        # 真的金流商會回傳它網站上的付款頁。我們的假付款頁就做在自己的網站上
        # （所有 API 都掛在 /api 底下，所以網址以 /api/payments 開頭）
        return f"/api/payments/mock-checkout/{trade_no}"

    def verify_callback(self, body: bytes, signature: str) -> bool:
        # 自己用密鑰重算一次簽章，跟通知附上的比對。
        # 一定要用 compare_digest，不要用 ==：
        # == 比到第一個不同的字元就停下來，攻擊者可以從回應快慢一點一點猜出正確簽章；
        # compare_digest 不管哪裡不同，花的時間都一樣。
        expected = sign(body, self._secret)
        # 兩邊都轉成 bytes 再比：簽章裡如果被塞了奇怪的字元，會回傳 False 而不是讓程式出錯
        return hmac.compare_digest(expected.encode(), signature.encode())

    def build_callback(
        self, trade_no: str, amount: int, success: bool
    ) -> tuple[bytes, str]:
        # 模擬「金流商伺服器」組出一則通知：內容轉成 JSON 位元組，再附上簽章。
        # 真實情況下這段是金流商做的，我們只負責收；這裡是為了假付款頁才需要它。
        body = json.dumps(
            {"trade_no": trade_no, "amount": amount, "success": success}
        ).encode()
        return body, sign(body, self._secret)
