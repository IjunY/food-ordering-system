"""The emails the account module sends, in Chinese and English together."""

from app.auth.models import User
from app.mail.sender import Email

# The app's name as the frontend shows it (frontend/js/i18n.js 'app.name')
APP_NAME_ZH = "NTHU 點餐系統"
APP_NAME_EN = "NTHU Food Ordering"


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


def signup_code_email(email: str, code: str, minutes: int) -> Email:
    """The sign-up verification code. The HTML version shows the code large and
    bold on its own line; the plain-text version is for mail apps without HTML."""
    body = f"""\
感謝您註冊 {APP_NAME_ZH}，以下是您的驗證碼：

{code}

驗證碼 {minutes} 分鐘內有效。如果不是您本人申請，請忽略這封信。

---

Thank you for signing up for {APP_NAME_EN}. Your verification code is:

{code}

The code works for {minutes} minutes. If you did not sign up, ignore this email.
"""
    code_html = (
        '<p style="margin:12px 0 20px;font-size:36px;font-weight:700;'
        'letter-spacing:8px;color:#5B2A86;font-family:Consolas,Menlo,monospace">'
        f"{code}</p>"
    )
    html = f"""\
<div style="font-family:'Noto Sans TC','Microsoft JhengHei',Arial,sans-serif;\
font-size:16px;line-height:1.6;color:#222;max-width:480px">
<p style="margin:0">感謝您註冊 {APP_NAME_ZH}，以下是您的驗證碼：</p>
{code_html}
<p style="margin:0;font-size:14px;color:#666">驗證碼 {minutes} 分鐘內有效。\
如果不是您本人申請，請忽略這封信。</p>
<hr style="margin:24px 0;border:0;border-top:1px solid #ddd">
<p style="margin:0">Thank you for signing up for {APP_NAME_EN}. \
Your verification code is:</p>
{code_html}
<p style="margin:0;font-size:14px;color:#666">The code works for {minutes} minutes. \
If you did not sign up, ignore this email.</p>
</div>
"""
    return Email(
        to=email,
        subject=f"註冊驗證碼 {code} Your sign-up code - {APP_NAME_ZH} {APP_NAME_EN}",
        body=body,
        html=html,
    )
