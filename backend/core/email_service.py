"""
core/email_service.py
──────────────────────
Email Dispatcher Module: Sends Email ID, Username, and Password to User Email.
Supports real SMTP (Gmail, SendGrid, Mailgun) and console dispatch logging.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings


def send_credentials_email(
    to_email: str,
    username: str,
    password: str,
    full_name: str = "Team Member",
    role: str = "STAFF",
    admin_email: str | None = None,
) -> dict:
    """
    Sends an HTML email containing login credentials to `to_email`
    AND dispatches an admin notification copy to `admin_email` (or settings.ADMIN_EMAIL).
    """

    subject = "Your PharmaCast Platform Login Credentials"
    login_url = f"{settings.APP_URL}/login"
    target_admin = admin_email or settings.ADMIN_EMAIL or settings.SMTP_USER

    # Build recipient list (recipient + admin)
    recipients = [to_email]
    if target_admin and target_admin.lower() not in [e.lower() for e in recipients]:
        recipients.append(target_admin)

    # HTML Email Template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #090d16; color: #e2e8f0; margin: 0; padding: 20px; }}
        .card {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #334155; border-radius: 16px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
        .header {{ text-align: center; margin-bottom: 24px; }}
        .logo {{ display: inline-block; width: 44px; height: 44px; line-height: 44px; background: linear-gradient(135deg, #6366f1, #06b6d4); color: #ffffff; font-weight: 900; font-size: 20px; border-radius: 12px; margin-bottom: 12px; }}
        .title {{ font-size: 20px; font-weight: 700; color: #ffffff; margin: 0; }}
        .subtitle {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
        .cred-box {{ background: #1e293b; border: 1px solid #475569; border-radius: 12px; padding: 20px; margin: 24px 0; }}
        .cred-item {{ margin-bottom: 12px; }}
        .cred-item:last-child {{ margin-bottom: 0; }}
        .label {{ font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
        .val {{ font-size: 15px; font-weight: 600; color: #38bdf8; font-family: monospace; margin-top: 2px; }}
        .val-pw {{ color: #34d399; font-size: 17px; background: #0f172a; padding: 6px 12px; border-radius: 6px; border: 1px solid #10b981; display: inline-block; margin-top: 4px; }}
        .btn {{ display: block; text-align: center; background: #4f46e5; color: #ffffff; font-weight: 700; font-size: 14px; text-decoration: none; padding: 12px 24px; border-radius: 10px; margin-top: 24px; }}
        .footer {{ font-size: 11px; color: #64748b; text-align: center; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <div class="logo">Rx</div>
          <h1 class="title">PharmaCast Credentials</h1>
          <p class="subtitle">Demand Intelligence & Strategy Platform</p>
        </div>

        <p style="font-size: 14px; color: #cbd5e1; margin-bottom: 16px;">Hello <strong>{full_name}</strong>,</p>
        <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
          An administrator has provisioned your account for the PharmaCast Demand & Strategy Platform. Your access credentials are provided below:
        </p>

        <div class="cred-box">
          <div class="cred-item">
            <div class="label">Email Address / Email ID</div>
            <div class="val">{to_email}</div>
          </div>
          <div class="cred-item" style="margin-top: 14px;">
            <div class="label">Username</div>
            <div class="val">{username}</div>
          </div>
          <div class="cred-item" style="margin-top: 14px;">
            <div class="label">Assigned Role</div>
            <div class="val" style="color: #a855f7;">{role}</div>
          </div>
          <div class="cred-item" style="margin-top: 14px;">
            <div class="label">Password</div>
            <div class="val-pw">{password}</div>
          </div>
        </div>

        <a href="{login_url}" class="btn">Sign In to Dashboard</a>

        <div class="footer">
          Please log in using your temporary password and update it via your account dashboard settings.<br>
          © 2026 PharmaCast Intelligence Platform.
        </div>
      </div>
    </body>
    </html>
    """

    # Print clean dispatch log in server console
    print("\n" + "=" * 60)
    print("[EMAIL DISPATCHER] Sending Account Credentials")
    print(f"   To User      : {to_email}")
    print(f"   Admin Copy   : {target_admin}")
    print(f"   Username     : {username}")
    print(f"   Role         : {role}")
    print(f"   Password     : {password}")
    print("=" * 60 + "\n")

    # Try SMTP Dispatch if credentials configured
    smtp_sent = False

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            sender_address = settings.SMTP_USER if "gmail.com" in settings.SMTP_HOST.lower() else (settings.SMTP_FROM_EMAIL or settings.SMTP_USER)

            for recipient in recipients:
                is_admin_copy = (recipient.lower() == target_admin.lower() and recipient.lower() != to_email.lower())
                msg_subject = f"[ADMIN COPY] {subject} - {to_email}" if is_admin_copy else subject

                msg = MIMEMultipart("alternative")
                msg["Subject"] = msg_subject
                msg["From"] = sender_address
                msg["To"] = recipient

                # Prepend Admin notification banner if recipient is Admin copy
                if is_admin_copy:
                    admin_banner = f"""
                    <div style="background: #1e1b4b; border: 1px solid #4338ca; color: #a5b4fc; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 12px;">
                      📌 <strong>ADMIN NOTIFICATION COPY:</strong> Credentials dispatched for user <strong>{full_name} ({to_email})</strong> [Role: {role}].
                    </div>
                    """
                    body_content = html_body.replace('<div class="header">', admin_banner + '<div class="header">')
                else:
                    body_content = html_body

                part = MIMEText(body_content, "html")
                msg.attach(part)

                if settings.SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        server.sendmail(sender_address, [recipient], msg.as_string())
                else:
                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                        server.ehlo()
                        server.starttls()
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        server.sendmail(sender_address, [recipient], msg.as_string())

            smtp_sent = True
            print(f"[OK] Real SMTP Email successfully delivered to {', '.join(recipients)}")
        except Exception as e:
            print(f"[WARNING] SMTP delivery notice ({e}). Logged to console instead.")
    else:
        print("[INFO] SMTP_USER/SMTP_PASSWORD not set in environment. Email logged to console.")

    return {
        "status": "sent" if (smtp_sent or not settings.SMTP_USER) else "failed",
        "to_email": to_email,
        "admin_email": target_admin,
        "username": username,
        "recipients": recipients,
        "smtp_delivered": smtp_sent,
        "notice": f"Real SMTP delivered to {', '.join(recipients)}" if smtp_sent else "Logged to server console",
    }
