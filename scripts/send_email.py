import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def get_config():
    return {
        "smtp_server": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "email": os.environ.get("SMTP_USER", ""),
        "app_password": os.environ.get("SMTP_PASSWORD", ""),
    }


def send_email(subject, body, to=None):
    config = get_config()
    if not config["email"] or not config["app_password"]:
        print(f"[{datetime.now()}] Email failed: SMTP_USER and SMTP_PASSWORD environment variables not set")
        return False
    to = to or config["email"]

    msg = MIMEMultipart()
    msg["From"] = config["email"]
    msg["To"] = to
    msg["Subject"] = f"[MainPixel Agent] {subject}"
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["email"], config["app_password"])
        server.sendmail(config["email"], to, msg.as_string())
        server.quit()
        print(f"[{datetime.now()}] Email sent: {subject}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Email failed: {e}")
        return False


def send_shift_start():
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")
    body = f"""
    <html><body>
    <h2>Hey Boss!</h2>
    <p>Today is <b>{date_str}</b> and I'm starting my shift at <b>{time_str}</b>.</p>
    <p>I'll be working on <b>MainPixel</b> - the school management SaaS platform.</p>
    <p>Current phase: <b>Phase 2 - Attendance Module</b></p>
    <p>Server: 178.105.115.123</p>
    <p>API: http://178.105.115.123:8000</p>
    <hr>
    <p><i>This is an automated message from your coding agent.</i></p>
    </body></html>
    """
    return send_email("Shift Started", body)


def send_shift_end():
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")
    body = f"""
    <html><body>
    <h2>Hey Boss!</h2>
    <p>Today is <b>{date_str}</b> and I'm finishing my shift at <b>{time_str}</b>.</p>
    <p>Summary of today's work is in the daily report email.</p>
    <hr>
    <p><i>This is an automated message from your coding agent.</i></p>
    </body></html>
    """
    return send_email("Shift Ended", body)


def send_update(subject, details):
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y %H:%M")
    body = f"""
    <html><body>
    <h2>Update from your coding agent</h2>
    <p><b>Date:</b> {date_str}</p>
    <p><b>Details:</b></p>
    <pre>{details}</pre>
    <hr>
    <p><i>This is an automated message from your coding agent.</i></p>
    </body></html>
    """
    return send_email(subject, body)


def send_daily_report(report):
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    body = f"""
    <html><body>
    <h2>Daily Report - {date_str}</h2>
    {report}
    <hr>
    <p><i>This is an automated message from your coding agent.</i></p>
    </body></html>
    """
    return send_email("Daily Report", body)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python send_email.py [shift_start|shift_end|update|report] [subject] [body]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "shift_start":
        send_shift_start()
    elif action == "shift_end":
        send_shift_end()
    elif action == "update":
        send_update(sys.argv[2] if len(sys.argv) > 2 else "Update", sys.argv[3] if len(sys.argv) > 3 else "No details")
    elif action == "report":
        send_daily_report(sys.argv[2] if len(sys.argv) > 2 else "No report")
    else:
        print(f"Unknown action: {action}")
