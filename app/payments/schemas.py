# API 的輸入與輸出格式（Pydantic）。
# FastAPI 會用這些 class 自動檢查收到的資料，也會用它們產生 /docs 文件。

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.payments.states import PaymentStatus


class PaymentCreate(BaseModel):
    # 前端要開始付款時，只需要告訴我們「哪一張訂單」。
    # 注意這裡刻意「沒有 amount 欄位」：金額一律由後端從資料庫算，前端就算塞了價格也用不到。
    order_id: int = Field(gt=0)  # gt=0：編號一定是正整數，否則自動回 422


class PaymentRead(BaseModel):
    # from_attributes=True：允許直接把資料庫的 Payment 物件轉成這個格式
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: int
    status: PaymentStatus
    expires_at: datetime
    paid_at: datetime | None


class PaymentCreated(BaseModel):
    # 建立付款後回傳給前端的內容：付款資料，加上要把使用者導去的付款頁網址
    payment: PaymentRead
    checkout_url: str


class CallbackPayload(BaseModel):
    # 金流商通知我們的內容。真實金流商的欄位名稱會不一樣，接的時候照它的文件改就好
    trade_no: str = Field(min_length=1, max_length=64)  # 是哪一筆交易
    amount: int  # 金流商實際收到多少錢
    success: bool  # 成功還是失敗
