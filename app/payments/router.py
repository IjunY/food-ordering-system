# 付款的 API 路由：接收 HTTP 請求、呼叫 service、把結果轉成 HTTP 回應。
# 這裡不寫業務規則，也不寫資料庫查詢。
# service 丟出的錯誤（NotFoundError 等）不用在這裡處理，main.py 會統一轉成 HTTP 錯誤。

from html import escape  # 把 < > & 等符號轉成安全的寫法，防止 XSS 攻擊
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.dependencies import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.payments import service
from app.payments.config import PaymentSettings, get_payment_settings
from app.payments.models import Payment
from app.payments.provider import LinePayProvider, MockProvider, PaymentProvider
from app.payments.schemas import PaymentCreate, PaymentCreated, PaymentRead
from app.payments.states import PaymentStatus

# prefix：這個檔案裡所有網址前面都會自動加上 /payments
# （main.py 掛上來時還會再加 /api，所以完整網址是 /api/payments/...）
# tags：在 /docs 頁面把付款相關的 API 歸成同一組
router = APIRouter(prefix="/payments", tags=["payments"])


# ---------- 依賴（Dependencies） ----------
# FastAPI 的 Depends 會在每次請求時自動呼叫這些函式，把結果傳進路由函式。
# 測試時可以用 app.dependency_overrides 換成假的，這就是「依賴注入」。
#
# 從 auth 匯入的兩個現成依賴：
#   DbSession   → 這次請求用的資料庫連線
#   CurrentUser → 目前登入的使用者；沒登入或 token 無效，會自動回 401

# Annotated[型別, Depends(...)] 是把「型別」和「從哪裡取得」寫在一起，取個短名字方便重複使用
SettingsDep = Annotated[PaymentSettings, Depends(get_payment_settings)]


def get_mock_provider(settings: SettingsDep) -> MockProvider:
    # get_secret_value() 取出 SecretStr 裡真正的字串
    return MockProvider(settings.webhook_secret.get_secret_value())


def get_provider(request: Request, settings: SettingsDep) -> PaymentProvider:
    # 照設定選金流商（.env 的 PAYMENT_PROVIDER）
    if settings.provider == "linepay":
        return get_linepay_provider(request, settings)
    return get_mock_provider(settings)


def get_linepay_provider(request: Request, settings: SettingsDep) -> LinePayProvider:
    return LinePayProvider(
        channel_id=settings.linepay_channel_id,
        channel_secret=settings.linepay_channel_secret.get_secret_value(),
        api_url=settings.linepay_api_url,
        # 付款完成後 LINE Pay 把瀏覽器導回這個網站（使用者現在開的網址）
        app_url=str(request.base_url),
    )


ProviderDep = Annotated[PaymentProvider, Depends(get_provider)]
MockProviderDep = Annotated[MockProvider, Depends(get_mock_provider)]
LinePayDep = Annotated[LinePayProvider, Depends(get_linepay_provider)]


async def get_raw_body(request: Request) -> bytes:
    # 驗證簽章必須用「原始的位元組」，不能用解析過的 JSON（空白、順序不同，簽章就會對不上）
    return await request.body()


def require_mock_enabled(request: Request, settings: SettingsDep) -> None:
    # 假付款頁只能在開發和測試環境使用，正式環境（prod）一律回 404，假裝不存在。
    # 否則任何人都能在正式網站上按「模擬付款成功」白吃白喝。
    # 改用 LINE Pay 之後也關掉：只能走真的金流商
    if request.app.state.app_settings.app_env == "prod" or settings.provider != "mock":
        raise NotFoundError("Not found")


def require_linepay(settings: SettingsDep) -> None:
    if settings.provider != "linepay":
        raise NotFoundError("Not found")


def _back_to_order(order_id: int, paid: bool) -> RedirectResponse:
    # 付款完成回到取餐券；沒完成回到付款頁（前端會說上一次沒付成功，可以再試一次）
    return RedirectResponse(
        f"/#paid-{order_id}" if paid else f"/#pay-{order_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ---------- API ----------


# status_code=201：成功建立資源時回 201 Created
# response_model：回傳的資料會照 PaymentCreated 的格式整理、過濾
@router.post("", response_model=PaymentCreated, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,  # FastAPI 會自動把請求的 JSON 轉成 PaymentCreate，格式錯誤回 422
    session: DbSession,
    user: CurrentUser,
    provider: ProviderDep,
    settings: SettingsDep,
) -> PaymentCreated:
    """開始付款：前端傳訂單編號，回傳付款頁網址。"""
    payment, checkout_url = service.create_payment(
        session, user, provider, settings, data.order_id
    )
    return PaymentCreated(
        payment=PaymentRead.model_validate(payment), checkout_url=checkout_url
    )


@router.get("/config")
def payment_config(settings: SettingsDep) -> dict[str, str]:
    """前端用：目前接的是哪個金流商（mock 或 linepay），付款頁顯示對應的選項。"""
    return {"provider": settings.provider}


# ---------- LINE Pay 付款完成／取消後，瀏覽器被導回來的網址 ----------
# 這兩個網址不檢查登入（是 LINE Pay 把瀏覽器導回來，不會帶我們的 token）：
# 付款成功與否由伺服器向 LINE Pay 確認，不是看網址裡寫什麼。


@router.get(
    "/linepay/confirm",
    dependencies=[Depends(require_linepay)],
    include_in_schema=False,
)
def linepay_confirm(
    session: DbSession,
    provider: LinePayDep,
    transaction_id: Annotated[str, Query(alias="transactionId", max_length=64)],
    trade_no: Annotated[str, Query(alias="orderId", max_length=64)],
) -> RedirectResponse:
    payment = service.confirm_linepay(session, provider, trade_no, transaction_id)
    return _back_to_order(payment.order_id, payment.status == PaymentStatus.PAID)


@router.get(
    "/linepay/cancel",
    dependencies=[Depends(require_linepay)],
    include_in_schema=False,
)
def linepay_cancel(
    session: DbSession, trade_no: Annotated[str, Query(max_length=64)]
) -> RedirectResponse:
    payment = service.cancel_checkout(session, trade_no)
    return _back_to_order(payment.order_id, payment.status == PaymentStatus.PAID)


@router.post("/callback")
def payment_callback(
    session: DbSession,
    provider: ProviderDep,
    body: Annotated[bytes, Depends(get_raw_body)],
    # Header()：從 HTTP 標頭讀值。參數 x_signature 對應標頭 X-Signature
    x_signature: Annotated[str, Header()],
) -> dict[str, bool]:
    """金流商通知付款結果（伺服器對伺服器）。

    這個網址不需要登入：呼叫它的是金流商的伺服器，不是使用者。
    安全性靠的是簽章，沒有正確簽章的通知一律拒絕。
    """
    service.handle_callback(session, provider, body, x_signature)
    return {"ok": True}


@router.get("/order/{order_id}", response_model=PaymentRead)
def get_payment_for_order(
    order_id: int, session: DbSession, user: CurrentUser
) -> Payment:
    """查某張訂單最新的付款，讓前端知道這張訂單付了沒。"""
    return service.get_payment_for_order(session, user, order_id)


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, session: DbSession, user: CurrentUser) -> Payment:
    """查詢付款狀態，讓前端顯示「付款成功」或「處理中」。"""
    return service.get_payment(session, user, payment_id)


# ---------- 假付款頁（只在開發和展示時使用） ----------
# 這兩個網址不檢查登入：瀏覽器直接開網頁、送表單時，不會帶著登入用的 token。
# 改用 trade_no 當通行證：它是 32 個字元的隨機字串，只有建立付款的本人拿得到。
# 真正的金流商付款頁也是這樣運作的。


@router.get(
    "/mock-checkout/{trade_no}",
    response_class=HTMLResponse,  # 回傳 HTML 網頁，不是 JSON
    dependencies=[Depends(require_mock_enabled)],
    include_in_schema=False,  # 不顯示在 /docs，因為它不是正式 API
)
def mock_checkout_page(trade_no: str, session: DbSession) -> str:
    """模擬金流商的付款頁：顯示金額和兩個按鈕。"""
    payment = service.get_payment_by_trade_no(session, trade_no)

    # 放進 HTML 的文字一律先 escape，防止 XSS
    action = f"/api/payments/mock-checkout/{escape(payment.trade_no)}/complete"
    return f"""<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>模擬付款</title></head>
<body>
  <h1>模擬付款頁</h1>
  <p>訂單編號：{payment.order_id}</p>
  <p>應付金額：NT$ {payment.amount}</p>
  <form method="post" action="{action}?success=true">
    <button type="submit">模擬付款成功</button>
  </form>
  <form method="post" action="{action}?success=false">
    <button type="submit">模擬付款失敗</button>
  </form>
</body>
</html>"""


@router.post(
    "/mock-checkout/{trade_no}/complete",
    response_class=HTMLResponse,
    dependencies=[Depends(require_mock_enabled)],
    include_in_schema=False,
)
def mock_checkout_complete(
    trade_no: str, success: bool, session: DbSession, provider: MockProviderDep
) -> str:
    """使用者按下按鈕後：扮演金流商，送出一則有簽章的通知給我們自己。"""
    payment = service.get_payment_by_trade_no(session, trade_no)
    # 真實世界裡，這一步是金流商的伺服器呼叫我們的 /api/payments/callback。
    # 這裡在同一個程式裡直接呼叫，但走的是同一段驗證流程，所以簽章、金額檢查一樣有效
    body, signature = provider.build_callback(payment.trade_no, payment.amount, success)
    payment = service.handle_callback(session, provider, body, signature)
    # 回到這張訂單：付好了看取餐券，沒付成功回付款頁
    paid = payment.status == PaymentStatus.PAID
    back = f"/#paid-{payment.order_id}" if paid else f"/#pay-{payment.order_id}"

    return f"""<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>付款結果</title></head>
<body>
  <h1>付款結果：{escape(payment.status.value)}</h1>
  <p>訂單編號：{payment.order_id}，金額：NT$ {payment.amount}</p>
  <p><a href="{back}">回到點餐系統</a></p>
</body>
</html>"""
