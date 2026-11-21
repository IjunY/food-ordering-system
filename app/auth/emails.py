"""The emails the account module sends, in Chinese and English together."""

from app.auth.models import User
from app.mail.sender import Email


def password_reset_email(user: User, link: str, minutes: int) -> Email:
    body = f"""\
{user.student_id} 您好：

我們收到重設 NTHU 點餐系統密碼的要求。請在 {minutes} 分鐘內打開下面的連結，設定新密碼：

{link}

連結只能用一次。如果不是您本人要求的，請忽略這封信，您的密碼不會改變。

---

Hello {user.student_id},

We received a request to reset your NTHU Food Ordering password. Open the link
below within {minutes} minutes to choose a new one:

{link}

The link works once. If you did not ask for this, ignore this email; your
password stays the same.
"""
    return Email(
        to=user.email,
        subject="重設密碼 Reset your password - NTHU 點餐 NTHU Food Ordering",
        body=body,
    )
