import imaplib
import email
import json
import os
import time
import subprocess
from datetime import datetime
from email.header import decode_header

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "email_config.json")
LAST_CHECK_PATH = os.path.join(os.path.dirname(__file__), ".last_email_check")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_last_check():
    if os.path.exists(LAST_CHECK_PATH):
        with open(LAST_CHECK_PATH) as f:
            return f.read().strip()
    return None


def save_last_check(date_str):
    with open(LAST_CHECK_PATH, "w") as f:
        f.write(date_str)


def decode_mime_header(header):
    if header is None:
        return ""
    decoded_parts = decode_header(header)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def check_emails():
    config = load_config()
    last_check = get_last_check()

    try:
        mail = imaplib.IMAP4_SSL(config["smtp_server"])
        mail.login(config["email"], config["app_password"])
        mail.select("INBOX")

        if last_check:
            status, messages = mail.search(None, f'(SINCE "{last_check}")')
        else:
            status, messages = mail.search(None, "UNSEEN")

        if status != "OK":
            return []

        email_ids = messages[0].split()
        new_emails = []

        for eid in email_ids:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_mime_header(msg["Subject"])
            from_addr = decode_mime_header(msg["From"])
            date_str = msg["Date"]

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            new_emails.append({
                "id": eid.decode(),
                "from": from_addr,
                "subject": subject,
                "body": body,
                "date": date_str,
            })

        mail.logout()
        save_last_check(datetime.now().strftime("%d-%b-%Y"))
        return new_emails

    except Exception as e:
        print(f"[{datetime.now()}] Email check failed: {e}")
        return []


def process_command(email_data):
    subject = email_data["subject"].lower()
    body = email_data["body"].strip()

    if "stop" in subject or "shutdown" in subject:
        subprocess.Popen(["python3", os.path.join(os.path.dirname(__file__), "send_email.py"), "update", "Shutdown Received", "Boss sent shutdown command. Stopping work."])
        return "shutdown"
    elif "priority" in subject or "urgent" in subject:
        subprocess.Popen(["python3", os.path.join(os.path.dirname(__file__), "send_email.py"), "update", "Priority Received", f"Boss wants priority work: {body}"])
    else:
        subprocess.Popen(["python3", os.path.join(os.path.dirname(__file__), "send_email.py"), "update", "Email Received", f"From: {email_data['from']}<br>Subject: {email_data['subject']}<br>Body: {body}"])

    return "ok"


def run_checker():
    interval = load_config()["check_interval"]
    print(f"[{datetime.now()}] Email checker started. Checking every {interval}s")

    while True:
        emails = check_emails()
        if emails:
            print(f"[{datetime.now()}] Found {len(emails)} new email(s)")
            for e in emails:
                result = process_command(e)
                if result == "shutdown":
                    print("Shutdown command received. Exiting.")
                    return
        time.sleep(interval)


if __name__ == "__main__":
    run_checker()
