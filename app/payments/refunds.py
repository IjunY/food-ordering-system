# 退款：訂單被取消時，把已經付的錢退回去。
#
# 這是給訂單模組呼叫的（app/orders/service.py 取消訂單時）。這個檔案刻意不 import
# order_gateway／orders，訂單模組才能 import 它，而不會變成兩個模組互相 import。

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import BadGatewayError
from app.payments import repo
from app.payments.models import Payment
from app.payments.provider import PaymentProvider, PaymentProviderError
from app.payments.states import PaymentStatus

logger = logging.getLogger(__name__)


def refund_order(
    session: Session, provider: PaymentProvider, order_id: int
) -> Payment | None:
    """訂單要被取消了：如果它已經付款，就向金流商全額退款，並把付款改成 REFUNDED。

    回傳被退款的那筆付款；這張訂單沒有已付款的付款（還沒付、到店付款）就回傳 None。

    呼叫的人要先鎖住訂單那一列（orders 的 get_order(for_update=True)），並在之後
    自己 commit：訂單改成「已取消」和付款改成「已退款」一起存檔。
    退款失敗會丟 BadGatewayError（502），什麼都不改，訂單也就不會被取消，可以再試一次。
    """
    payment = repo.get_paid_for_order(session, order_id, for_update=True)
    if payment is None:
        return None
    # 還在等付款（PENDING）的不用處理：訂單取消後，金流商說成功也只會變成 FAILED（見 service._finish）

    try:
        refund_ref = provider.refund(payment.provider_ref, payment.amount)
    except PaymentProviderError as exc:
        # 原因（例如 LINE Pay 的錯誤代碼）寫進伺服器的 log，畫面上只說「退款失敗，請再試一次」
        logger.warning("Refund for order %s failed: %s", order_id, exc)
        session.rollback()  # 什麼都不改，也放開訂單和付款的鎖
        raise BadGatewayError(
            "The payment could not be refunded, so the order was not cancelled. "
            "Please try again."
        ) from exc

    payment.status = PaymentStatus.REFUNDED
    payment.refunded_at = datetime.now(UTC)
    payment.refund_ref = refund_ref
    return payment
