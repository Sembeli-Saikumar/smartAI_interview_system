# app/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

MAIL_EMAIL    = os.getenv("MAIL_EMAIL")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL")
APP_URL       = os.getenv("APP_URL", "http://127.0.0.1:5000")


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Smart Interview System <{MAIL_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(MAIL_EMAIL, MAIL_PASSWORD)
            server.sendmail(MAIL_EMAIL, to_email, msg.as_string())
        print(f"[Email] ✅ Sent to {to_email}")
        return True
    except Exception as e:
        print(f"[Email Error] ❌ {e}")
        return False


def _base_template(content: str) -> str:
    """Common email wrapper with light blue theme"""
    return f"""
    <div style="font-family:'DM Sans',Arial,sans-serif;background:#f0f7ff;padding:40px 16px;min-height:100vh;">
      <div style="max-width:560px;margin:0 auto;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e6091,#168aad);border-radius:16px;padding:28px;text-align:center;margin-bottom:24px;">
          <h1 style="color:#fff;margin:0;font-size:1.6rem;letter-spacing:-.01em;">
            🎯 Smart Interview System
          </h1>
          <p style="color:rgba(255,255,255,.7);margin:6px 0 0;font-size:.85rem;">
            AI-Powered Interview Platform
          </p>
        </div>

        <!-- Content -->
        <div style="background:#fff;border:1px solid #d0e8f2;border-radius:16px;padding:32px;margin-bottom:16px;box-shadow:0 4px 20px rgba(30,96,145,.08);">
          {content}
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:16px;color:#5a7d90;font-size:.75rem;">
          Smart Interview System &nbsp;·&nbsp; This is an automated email, please do not reply.
        </div>

      </div>
    </div>
    """


# ── 1. Interviewer Register hone par — Interviewer ko Welcome Mail ──────────
def send_interviewer_welcome_on_register(name: str, email: str) -> bool:
    subject = "🎉 Welcome to Smart Interview System — Account Created!"
    content = f"""
        <h2 style="color:#0d2d3f;margin:0 0 8px;">Hi {name}! 👋</h2>
        <p style="color:#5a7d90;margin:0 0 20px;">
          Your <strong>Interviewer account</strong> has been successfully created on
          Smart Interview System.
        </p>

        <div style="background:#f0f7ff;border:1px solid #d0e8f2;border-radius:12px;padding:16px;margin-bottom:20px;">
          <p style="margin:0 0 8px;color:#0d2d3f;font-size:.9rem;">
            <strong>📧 Email:</strong>
            <span style="color:#1e6091;">{email}</span>
          </p>
          <p style="margin:0;color:#0d2d3f;font-size:.9rem;">
            <strong>👤 Role:</strong>
            <span style="color:#1e6091;">Interviewer</span>
          </p>
        </div>

        <div style="background:rgba(30,96,145,.06);border-left:4px solid #1e6091;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:24px;">
          <p style="margin:0;color:#1e6091;font-size:.85rem;">
            💡 <strong>Next Steps:</strong> Login with your registered email and password.
            Upload your resume and start your AI mock interviews!
          </p>
        </div>

        <a href="{APP_URL}/auth/login"
           style="display:block;text-align:center;background:linear-gradient(135deg,#1e6091,#168aad);
                  color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;
                  font-weight:700;font-size:1rem;box-shadow:0 4px 16px rgba(30,96,145,.25);">
          🚀 Login to Your Account
        </a>
    """
    return send_email(email, subject, _base_template(content))


# ── 2. Interviewer Register hone par — Admin ko Notification ────────────────
def send_interviewer_registered_admin(name: str, email: str) -> bool:
    subject = f"🆕 New Interviewer Registered — {name}"
    content = f"""
        <h2 style="color:#0d2d3f;margin:0 0 8px;">New Interviewer Registered! 🎉</h2>
        <p style="color:#5a7d90;margin:0 0 20px;">
          A new interviewer has just registered on Smart Interview System.
        </p>

        <div style="background:#f0f7ff;border:1px solid #d0e8f2;border-radius:12px;padding:16px;margin-bottom:20px;">
          <p style="margin:0 0 10px;color:#0d2d3f;">
            <strong>👤 Name:</strong>
            <span style="color:#1e6091;font-weight:600;">{name}</span>
          </p>
          <p style="margin:0 0 10px;color:#0d2d3f;">
            <strong>📧 Email:</strong>
            <span style="color:#1e6091;">{email}</span>
          </p>
          <p style="margin:0;color:#0d2d3f;">
            <strong>🕐 Time:</strong>
            <span style="color:#5a7d90;">Just now</span>
          </p>
        </div>

        <div style="background:rgba(184,104,10,.06);border-left:4px solid #b8680a;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:24px;">
          <p style="margin:0;color:#b8680a;font-size:.85rem;">
            ⚠️ <strong>Action Required:</strong> Review this interviewer's account in
            your admin panel. You can activate or deactivate their access anytime.
          </p>
        </div>

        <a href="{APP_URL}/admin/dashboard"
           style="display:block;text-align:center;background:linear-gradient(135deg,#1e6091,#168aad);
                  color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;
                  font-weight:700;font-size:1rem;box-shadow:0 4px 16px rgba(30,96,145,.25);">
          👉 Go to Admin Panel
        </a>
    """
    return send_email(ADMIN_EMAIL, subject, _base_template(content))


# ── 3. Admin ne Interviewer add kiya — Credentials mail ─────────────────────
def send_interviewer_welcome(name: str, email: str, password: str) -> bool:
    subject = "🎉 Your Interviewer Account is Ready — Smart Interview System"
    content = f"""
        <h2 style="color:#0d2d3f;margin:0 0 8px;">Hi {name}! 👋</h2>
        <p style="color:#5a7d90;margin:0 0 20px;">
          Your <strong>Interviewer account</strong> has been created by the Admin.
          Here are your login credentials:
        </p>

        <div style="background:#f0f7ff;border:1px solid #d0e8f2;border-radius:12px;padding:20px;margin-bottom:20px;">
          <p style="margin:0 0 12px;color:#0d2d3f;">
            <strong>📧 Email:</strong>
            <span style="color:#1e6091;font-weight:600;">{email}</span>
          </p>
          <p style="margin:0;color:#0d2d3f;">
            <strong>🔑 Password:</strong>
            <span style="background:#e8f4fd;color:#1e6091;font-family:monospace;
                         padding:4px 10px;border-radius:6px;font-weight:700;font-size:1rem;">
              {password}
            </span>
          </p>
        </div>

        <div style="background:rgba(26,122,74,.06);border-left:4px solid #1a7a4a;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:24px;">
          <p style="margin:0;color:#1a7a4a;font-size:.85rem;">
            🔒 <strong>Security Tip:</strong> Please change your password after first login
            from your Profile Settings.
          </p>
        </div>

        <a href="{APP_URL}/auth/login"
           style="display:block;text-align:center;background:linear-gradient(135deg,#1e6091,#168aad);
                  color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;
                  font-weight:700;font-size:1rem;box-shadow:0 4px 16px rgba(30,96,145,.25);">
          🚀 Login Now
        </a>
    """
    return send_email(email, subject, _base_template(content))


# ── 4. Schedule Approved ─────────────────────────────────────────────────────
def send_schedule_approved(candidate_name: str, candidate_email: str,
                           title: str, scheduled_at: str,
                           interviewer_name: str = None) -> bool:
    subject = f"✅ Interview Approved — {title}"
    content = f"""
        <h2 style="color:#0d2d3f;margin:0 0 8px;">Hi {candidate_name}! 🎉</h2>
        <p style="color:#5a7d90;margin:0 0 20px;">
          Your interview has been <strong style="color:#1a7a4a;">approved</strong>!
          Here are the details:
        </p>

        <div style="background:#f0f7ff;border:1px solid #d0e8f2;border-radius:12px;padding:20px;margin-bottom:20px;">
          <p style="margin:0 0 10px;color:#0d2d3f;">
            <strong>📋 Title:</strong>
            <span style="color:#1e6091;">{title}</span>
          </p>
          <p style="margin:0 0 10px;color:#0d2d3f;">
            <strong>📅 Date & Time:</strong>
            <span style="color:#1e6091;font-weight:600;">{scheduled_at}</span>
          </p>
          {'<p style="margin:0;color:#0d2d3f;"><strong>👤 Interviewer:</strong> <span style="color:#1e6091;">' + interviewer_name + '</span></p>' if interviewer_name else ''}
        </div>

        <a href="{APP_URL}/interview/start"
           style="display:block;text-align:center;background:linear-gradient(135deg,#1e6091,#168aad);
                  color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;
                  font-weight:700;font-size:1rem;box-shadow:0 4px 16px rgba(30,96,145,.25);">
          🎯 Start Interview
        </a>
    """
    return send_email(candidate_email, subject, _base_template(content))