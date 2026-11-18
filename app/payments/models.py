# payments 資料表的定義（SQLAlchemy ORM）。
# 一個 class 對應一張表，一個屬性對應一個欄位。寫法照 orders/models.py。

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.payments.states import PaymentStatus


class Payment(Base):
    # 資料庫裡的表名
    __tablename__ = "payments"

    # __table_args__ 放「整張表」層級的規則，資料庫會幫我們強制執行
    __table_args__ = (
        # 規則 1：金額一定大於 0。就算程式寫錯，資料庫也會拒絕存入 0 元或負數。
        # 實際的名稱會照 core/db.py 的命名規則變成 ck_payments_amount_positive
        CheckConstraint("amount > 0", name="amount_positive"),
        # 規則 2：同一張訂單，最多只能有一筆「進行中或已付款」的付款。
        # 這是「部分唯一索引」：只對 status 是 PENDING 或 PAID 的那些列檢查 order_id 不重複。
        # 效果：同一張訂單不可能被付兩次，也不會同時有兩筆待付款。
        # FAILED、EXPIRED 不受限制，所以付款失敗後可以再建立一筆新的重試。
        # （資料庫裡存的是列舉的「名稱」PENDING / PAID，不是小寫的值，所以這裡寫大寫）
        Index(
            "uq_payments_order_id_active",
            "order_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'PAID')"),
        ),
    )

    # 主鍵：每筆付款的編號，資料庫自動遞增
    id: Mapped[int] = mapped_column(primary_key=True)

    # 外鍵：指向 orders 表的 id，代表「這筆付款屬於哪張訂單」。index=True 讓用訂單查付款比較快
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)

    # 金額，單位是新台幣「元」，用整數存，不用 float（避免 0.1 + 0.2 != 0.3 的誤差）
    amount: Mapped[int] = mapped_column()

    # 付款狀態。native_enum=False 表示在資料庫存成一般字串欄位（跟 orders 的寫法一致）
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False), default=PaymentStatus.PENDING
    )

    # 交易編號：我們自己產生、交給金流商的唯一編號。金流商通知時會帶著它，我們靠它找到這筆付款。
    # unique=True：資料庫保證不會有兩筆付款用同一個編號
    trade_no: Mapped[str] = mapped_column(String(64), unique=True)

    # 建立時間。server_default=func.now() 表示由資料庫在新增時自動填入現在時間
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 付款期限，超過就視為逾時
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # 付款成功的時間。還沒付款時是 None（資料庫裡是 NULL）
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
