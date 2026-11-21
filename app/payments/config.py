# 付款模組自己的設定。
# 放在 payments 裡而不是 core/config.py，是為了不去改別人負責的檔案。

# lru_cache：函式第一次被呼叫時算出結果，之後直接回傳同一個結果（只讀一次 .env）
from functools import lru_cache
from typing import Literal, Self

# Field 用來替欄位加上限制；SecretStr 會把值藏起來，印出來只會看到 '**********'
from pydantic import Field, SecretStr, model_validator

# BaseSettings 會自動從環境變數和 .env 檔讀值
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentSettings(BaseSettings):
    # env_prefix="PAYMENT_"：欄位 webhook_secret 會去讀環境變數 PAYMENT_WEBHOOK_SECRET
    # extra="ignore"：.env 裡其他不相關的變數（例如 DATABASE_URL）直接忽略
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="PAYMENT_", extra="ignore"
    )

    # 和金流商共用的密鑰，用來驗證通知是不是偽造的。
    # 刻意不給預設值：沒有設定的話程式會直接報錯，避免用一把大家都知道的密鑰上線。
    # min_length=32：太短的密鑰容易被猜到（跟 core/config.py 的 jwt_secret 同樣標準）
    webhook_secret: SecretStr = Field(min_length=32)

    # 付款期限（分鐘）。gt=0 表示一定要大於 0
    expire_minutes: int = Field(default=15, gt=0)

    # 用哪個金流商：mock（自己網站上的假付款頁）或 linepay（LINE Pay）
    provider: Literal["mock", "linepay"] = "mock"

    # LINE Pay 的商店資料（provider=linepay 時一定要有）。
    # 到 https://pay.line.me/tw/developers/techsupport/sandbox/creation 申請 sandbox，會寄來 Channel ID 和 Channel Secret
    linepay_channel_id: str = ""
    linepay_channel_secret: SecretStr = SecretStr("")
    # 預設是 sandbox（測試環境，不會真的扣款）；正式上線才改成 https://api-pay.line.me
    linepay_api_url: str = "https://sandbox-api-pay.line.me"

    @model_validator(mode="after")
    def linepay_needs_keys(self) -> Self:
        if self.provider == "linepay" and not (
            self.linepay_channel_id and self.linepay_channel_secret.get_secret_value()
        ):
            raise ValueError(
                "PAYMENT_PROVIDER=linepay needs PAYMENT_LINEPAY_CHANNEL_ID and "
                "PAYMENT_LINEPAY_CHANNEL_SECRET in .env"
            )
        return self


@lru_cache
def get_payment_settings() -> PaymentSettings:
    # pydantic 會在建立物件時自動讀環境變數，所以這裡不用傳參數
    return PaymentSettings()  # pyright: ignore[reportCallIssue]
