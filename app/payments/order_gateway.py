# 付款模組「向訂單模組要資料」的唯一出入口。
#
# 付款需要知道訂單的金額、狀態、是誰下的單，但 orders 是別人負責的模組。
# 把所有跟 orders 有關的程式集中在這個檔案，之後 orders 改了寫法，
# 只要改這裡，service.py 完全不用動。

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.models import User
from app.orders import repo as orders_repo
from app.orders import service as orders_service
from app.orders.models import Order
from app.orders.states import OrderStatus


# dataclass 會自動幫我們產生 __init__ 等方法；frozen=True 表示建立後不能修改
@dataclass(frozen=True)
class OrderInfo:
    """付款模組需要知道的訂單資訊（只有這幾個欄位，其他的我們不關心）。"""

    id: int
    user_id: int  # 下單者的帳號 id（User.id）
    status: OrderStatus
    total: int  # 訂單總金額（元）


def _to_info(order: Order) -> OrderInfo:
    # 金額由後端自己算：每個品項的「下單當下單價」× 數量，再全部加總。
    # unit_price 是下單時存下的價格快照，店家之後改價也不會影響這張訂單。
    total = sum(item.unit_price * item.quantity for item in order.items)
    return OrderInfo(
        id=order.id, user_id=order.user_id, status=order.status, total=total
    )


def get_order_for_user(session: Session, user: User, order_id: int) -> OrderInfo:
    """以「某個使用者」的身分查訂單。

    直接用 orders 寫好的 get_order：訂單不存在、或不是這個人的（而且他不是店員），
    它都會丟出 NotFoundError（404），所以別人的訂單編號猜不出來。
    """
    return _to_info(orders_service.get_order(session, user, order_id))


def get_order_for_callback(session: Session, order_id: int) -> OrderInfo | None:
    """金流商通知進來時查訂單。

    通知是金流商的伺服器送來的，沒有「登入的使用者」，所以不能用上面那個函式。
    for_update=True 會把訂單這一列鎖住，確保我們檢查狀態的同時，訂單不會剛好被取消。
    """
    order = orders_repo.get(session, order_id, for_update=True)
    return None if order is None else _to_info(order)
