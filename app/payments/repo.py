# 資料存取層：整個付款模組「只有這個檔案」會寫資料庫查詢。
# service.py 要資料就呼叫這裡的函式，不自己寫查詢。

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import Payment
from app.payments.states import PaymentStatus

# 「進行中或已付款」的狀態，對應 models.py 裡那個部分唯一索引
ACTIVE_STATUSES = (PaymentStatus.PENDING, PaymentStatus.PAID)


def add(session: Session, payment: Payment) -> Payment:
    session.add(payment)  # 把新物件放進 session，準備寫入
    session.flush()  # 立刻送出 INSERT（但還沒 commit），這樣 payment.id 才會有值
    return payment


def get(session: Session, payment_id: int) -> Payment | None:
    # 用主鍵查一筆付款，找不到回傳 None
    return session.get(Payment, payment_id)


def get_by_trade_no(
    session: Session, trade_no: str, for_update: bool = False
) -> Payment | None:
    # select(Payment).where(...) 對應 SQL：SELECT * FROM payments WHERE trade_no = ?
    # SQLAlchemy 會自動用「參數化查詢」，所以不會有 SQL injection 的問題
    query = select(Payment).where(Payment.trade_no == trade_no)
    if for_update:
        # 對應 SQL 的 SELECT ... FOR UPDATE：把這一列「鎖住」，直到這次交易結束。
        # 如果同一則通知幾乎同時送來兩次，第二次會在這裡排隊等第一次處理完，
        # 等它拿到資料時，狀態已經是 PAID，就不會重複處理。
        query = query.with_for_update()
    # scalar()：取出第一筆 Payment 物件，沒有就回傳 None
    return session.scalar(query)


def get_active_for_order(session: Session, order_id: int) -> Payment | None:
    # 找某張訂單「進行中或已付款」的那一筆付款（因為唯一索引，最多只會有一筆）
    query = select(Payment).where(
        Payment.order_id == order_id,
        Payment.status.in_(ACTIVE_STATUSES),  # in_ 對應 SQL 的 IN (...)
    )
    return session.scalar(query)


def get_latest_for_order(session: Session, order_id: int) -> Payment | None:
    # 某張訂單「最新」的一筆付款：照編號由大到小排，只拿第一筆
    query = (
        select(Payment)
        .where(Payment.order_id == order_id)
        .order_by(Payment.id.desc())
        .limit(1)
    )
    return session.scalar(query)


def has_paid_payment(session: Session, order_id: int) -> bool:
    query = select(Payment.id).where(
        Payment.order_id == order_id,
        Payment.status == PaymentStatus.PAID,
    )
    # 查得到一筆就代表已付款；is not None 把結果轉成 True / False
    return session.scalar(query) is not None
