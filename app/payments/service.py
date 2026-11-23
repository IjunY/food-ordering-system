# 付款的核心邏輯（業務規則）都在這裡。
# router.py 負責「接收請求、回傳結果」，真正決定能不能付、怎麼改狀態的是這個檔案。
#
# 出錯時丟出 core/errors.py 的錯誤（NotFoundError、ConflictError…），
# main.py 裡的處理器會自動把它們轉成對應的 HTTP 狀態碼和 {"detail": "..."}。

import logging
import secrets  # 產生安全的隨機字串（比 random 模組安全，適合用在編號、token）
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.errors import (
    BadGatewayError,
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.orders.states import OrderStatus
from app.payments import order_gateway, repo
from app.payments.config import PaymentSettings
from app.payments.models import Payment
from app.payments.provider import (
    LinePayProvider,
    PaymentProvider,
    PaymentProviderError,
)
from app.payments.schemas import CallbackPayload
from app.payments.states import PaymentStatus, can_transition

logger = logging.getLogger(__name__)

# ---------- 小工具 ----------


def _now() -> datetime:
    # 一律使用帶時區的 UTC 時間，避免「台灣時間」和「伺服器時間」混在一起
    return datetime.now(UTC)


def _expire_if_overdue(payment: Payment) -> bool:
    # 如果是待付款、而且已經超過期限，就改成 EXPIRED。有改的話回傳 True
    if payment.status == PaymentStatus.PENDING and _now() >= payment.expires_at:
        payment.status = PaymentStatus.EXPIRED
        return True
    return False


def _checkout_url(session: Session, provider: PaymentProvider, payment: Payment) -> str:
    """付款頁網址：建立過就沿用；第一次就向金流商建立交易，把網址和交易編號存起來。"""
    if payment.checkout_url:
        return payment.checkout_url
    try:
        checkout = provider.create_checkout(payment.trade_no, payment.amount)
    except PaymentProviderError as exc:
        # 金流商建立交易失敗：這筆作廢（之後可以重試，會建立新的一筆）。
        # 原因（例如 LINE Pay 的錯誤代碼）寫進伺服器的 log，顧客只看到「暫時無法付款」
        logger.warning("Payment provider refused order %s: %s", payment.order_id, exc)
        payment.status = PaymentStatus.FAILED
        session.commit()
        raise BadGatewayError(
            "The payment provider is not available right now"
        ) from exc
    payment.checkout_url = checkout.url
    payment.provider_ref = checkout.provider_ref
    session.commit()
    return checkout.url


def _finish(session: Session, payment: Payment, success: bool) -> Payment:
    """金流商說「成功／失敗」之後，決定這筆付款的最終狀態並存檔（假付款通知和 LINE Pay 共用）。"""
    # 如果訂單在付款途中被取消了（不再是「確認中」），就算金流商說成功，
    # 也不能標成已付款，否則會出現「已取消卻已付款」的訂單。
    # （LINE Pay 不會走到這裡：confirm_linepay 看到訂單取消了就不向 LINE Pay 確認扣款。
    #   已經付好款的訂單之後才被取消，錢由 refunds.py 退回）
    order = order_gateway.get_order_for_callback(session, payment.order_id)
    order_open = order is not None and order.status == OrderStatus.CONFIRMING
    new_status = PaymentStatus.PAID if success and order_open else PaymentStatus.FAILED

    # 用狀態機確認這個轉換是合法的
    if not can_transition(payment.status, new_status):
        session.rollback()
        raise ConflictError("This payment can no longer be changed")

    payment.status = new_status
    if new_status == PaymentStatus.PAID:
        payment.paid_at = _now()
    session.commit()
    return payment


# ---------- 對外提供的功能 ----------


def create_payment(
    session: Session,
    user: User,
    provider: PaymentProvider,
    settings: PaymentSettings,
    order_id: int,
) -> tuple[Payment, str]:
    """為一張訂單建立付款，回傳（付款紀錄, 付款頁網址）。"""

    # 1. 向訂單模組查這張訂單。不存在、或不是這個人能看的訂單，這裡就會直接丟出 404
    order = order_gateway.get_order_for_user(session, user, order_id)

    # 2. 只有下單的本人可以付款。店員雖然看得到所有訂單，但不能替客人付款。
    #    一樣回 404，不透露「這張訂單存在」
    if order.user_id != user.id:
        raise NotFoundError("Order not found")

    # 3. 只有「確認中」的訂單可以付款；已取消、已在製作的都不行
    if order.status != OrderStatus.CONFIRMING or order.total <= 0:
        raise ConflictError("This order is not awaiting payment")

    # 4. 看看這張訂單是不是已經有付款紀錄
    existing = repo.get_active_for_order(session, order_id)
    if existing is not None:
        if _expire_if_overdue(existing):
            session.commit()  # 舊的那筆過期了，先存檔，下面就能建立新的
        elif existing.status == PaymentStatus.PAID:
            raise ConflictError("This order is already paid")
        else:
            # 還有一筆待付款、還沒過期：直接回傳同一筆，不重複建立。
            # 這樣使用者連按兩次「去付款」，也只會有一筆付款（冪等性）
            return existing, _checkout_url(session, provider, existing)

    # 5. 建立新的付款紀錄
    payment = Payment(
        order_id=order_id,
        amount=order.total,  # 金額來自後端計算，不是前端傳的
        status=PaymentStatus.PENDING,
        trade_no=secrets.token_hex(16),  # 32 個字元的隨機編號，猜不到
        expires_at=_now() + timedelta(minutes=settings.expire_minutes),
    )
    try:
        repo.add(session, payment)
        session.commit()  # 正式寫入資料庫
    except IntegrityError:
        # 撞到資料庫的唯一索引：代表「幾乎同一時間」另一個請求已經幫這張訂單建立了付款。
        # 這種情況第 4 步擋不住（兩個請求同時查，都查到「沒有」），靠的是資料庫這道最後防線。
        session.rollback()  # 取消這次失敗的寫入
        existing = repo.get_active_for_order(session, order_id)
        if existing is None or existing.status == PaymentStatus.PAID:
            raise ConflictError("This order is already paid") from None
        return existing, _checkout_url(session, provider, existing)

    # 6. 請金流商建立交易，拿到付款頁網址（和金流商的交易編號，一起存起來）
    return payment, _checkout_url(session, provider, payment)


def handle_callback(
    session: Session, provider: PaymentProvider, body: bytes, signature: str
) -> Payment:
    """處理金流商的付款結果通知。這是判斷「有沒有付款成功」的唯一依據。"""

    # 1. 驗證簽章：確定這則通知真的是金流商發的，內容也沒被改過
    if not provider.verify_callback(body, signature):
        raise BadRequestError("Invalid signature")

    # 2. 把 JSON 轉成 CallbackPayload，格式不對就拒絕
    try:
        data = CallbackPayload.model_validate_json(body)
    except ValidationError:
        raise BadRequestError("Invalid callback payload") from None

    # 3. 找到這筆付款，並且鎖住它（避免同一則通知同時被處理兩次）
    payment = repo.get_by_trade_no(session, data.trade_no, for_update=True)
    if payment is None:
        raise NotFoundError("Payment not found")

    # 4. 冪等性：已經處理過的（不是 PENDING）就什麼都不做，直接回傳。
    #    金流商常常會重送同一則通知，重送時回「成功」，它就不會再一直送。
    if payment.status != PaymentStatus.PENDING:
        session.commit()  # 沒有改任何東西，commit 只是結束交易、釋放鎖
        return payment

    # 5. 已經過期就作廢，不接受這次付款結果。
    #    真實金流商的付款頁也會設期限，所以正常情況下很少發生
    if _expire_if_overdue(payment):
        session.commit()
        return payment

    # 6. 金額要跟我們記錄的一模一樣，否則可能是被竄改過
    if data.amount != payment.amount:
        session.rollback()  # 釋放鎖，什麼都不改
        raise BadRequestError("Amount does not match")

    # 7. 決定新狀態、檢查轉換、存檔（見 _finish）
    return _finish(session, payment, data.success)


def confirm_linepay(
    session: Session, provider: LinePayProvider, trade_no: str, transaction_id: str
) -> Payment:
    """使用者在 LINE Pay 付款頁同意付款，被導回我們的網站之後：向 LINE Pay 確認扣款。

    導回來的網址誰都能打，所以不相信網址裡的任何東西：交易編號要和我們建立交易時
    LINE Pay 給的一樣，扣款成功與否也是我們的伺服器去問 LINE Pay。
    """
    payment = repo.get_by_trade_no(session, trade_no, for_update=True)
    if payment is None:
        raise NotFoundError("Payment not found")
    # 已經處理過（例如重新整理了這一頁）：什麼都不做
    if payment.status != PaymentStatus.PENDING:
        session.commit()
        return payment
    if _expire_if_overdue(payment):
        session.commit()
        return payment
    if payment.provider_ref is None or payment.provider_ref != transaction_id:
        session.rollback()
        raise BadRequestError(
            "This LINE Pay transaction does not belong to this payment"
        )

    # 訂單已經被取消：不要向 LINE Pay 確認（沒確認就不會扣款），直接作廢
    order = order_gateway.get_order_for_callback(session, payment.order_id)
    if order is None or order.status != OrderStatus.CONFIRMING:
        return _finish(session, payment, success=False)
    return _finish(session, payment, provider.confirm(transaction_id, payment.amount))


def cancel_checkout(session: Session, trade_no: str) -> Payment:
    """使用者在付款頁按了取消：這筆付款作廢（可以重新付款，會建立新的一筆）。"""
    payment = repo.get_by_trade_no(session, trade_no, for_update=True)
    if payment is None:
        raise NotFoundError("Payment not found")
    if payment.status == PaymentStatus.PENDING:
        payment.status = PaymentStatus.FAILED
    session.commit()
    return payment


def get_payment(session: Session, user: User, payment_id: int) -> Payment:
    """查詢一筆付款。順便檢查有沒有過期（不另外跑排程，查的時候順便處理）。"""
    payment = repo.get(session, payment_id)
    if payment is None:
        raise NotFoundError("Payment not found")
    try:
        # 能看這張訂單的人（下單的本人或店員）才能看它的付款
        order_gateway.get_order_for_user(session, user, payment.order_id)
    except NotFoundError:
        # 換成一樣的訊息：別人的付款看起來跟「不存在」一模一樣
        raise NotFoundError("Payment not found") from None
    if _expire_if_overdue(payment):
        session.commit()
    return payment


def get_payment_for_order(session: Session, user: User, order_id: int) -> Payment:
    """查某張訂單最新的一筆付款，讓前端知道這張訂單付了沒。"""
    order_gateway.get_order_for_user(session, user, order_id)  # 沒權限看訂單就是 404
    payment = repo.get_latest_for_order(session, order_id)
    if payment is None:
        raise NotFoundError("This order has no payment yet")
    if _expire_if_overdue(payment):
        session.commit()
    return payment


def get_payment_by_trade_no(session: Session, trade_no: str) -> Payment:
    payment = repo.get_by_trade_no(session, trade_no)
    if payment is None:
        raise NotFoundError("Payment not found")
    return payment


def is_order_paid(session: Session, order_id: int) -> bool:
    """給其他模組用：這張訂單付款了沒？
    例如 orders 可以規定「付款完成，店家才能把訂單改成製作中」。"""
    return repo.has_paid_payment(session, order_id)
