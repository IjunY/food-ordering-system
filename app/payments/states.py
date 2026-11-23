# 付款的「狀態機」：定義付款有哪些狀態，以及狀態之間可以怎麼轉換。
# 這個檔案是純 Python，不碰資料庫，所以最容易寫測試。

# StrEnum 是「值為字串的列舉」：PaymentStatus.PAID 既是列舉成員，也等於字串 "paid"
from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"  # 已建立付款，等使用者去付錢
    PAID = "paid"  # 金流商通知：付款成功
    FAILED = "failed"  # 金流商通知：付款失敗（例如卡被拒）
    EXPIRED = "expired"  # 超過期限沒付，自動作廢
    REFUNDED = "refunded"  # 付過錢的訂單被取消，錢已經退回去（app/payments/refunds.py）


# 允許的轉換表：key 是「目前狀態」，value 是「可以變成哪些狀態」
# 例如 PENDING 可以變成 PAID、FAILED、EXPIRED
_ALLOWED: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {
        PaymentStatus.PAID,
        PaymentStatus.FAILED,
        PaymentStatus.EXPIRED,
    },
    # 已付款只能再變成「已退款」（訂單被取消時）
    PaymentStatus.PAID: {PaymentStatus.REFUNDED},
    # 下面三個是「終點」：一旦到了就不能再變。
    # 想重新付款的話，是建立一筆「新的」付款，而不是把舊的改回 PENDING。
    PaymentStatus.FAILED: set(),
    PaymentStatus.EXPIRED: set(),
    PaymentStatus.REFUNDED: set(),
}


def can_transition(old: PaymentStatus, new: PaymentStatus) -> bool:
    # 查表：new 在 old 允許的集合裡，才回傳 True
    return new in _ALLOWED[old]
