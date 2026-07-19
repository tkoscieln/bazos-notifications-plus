import os
import json
import urllib.request
import urllib.parse
from imap_tools import MailBox, AND

# Configuration - Loaded from environment variables safely
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.getenv("EMAIL_USER", "your-burner-account@gmail.com")
EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD", "abcd-efgh-ijkl-mnop"
)  # 16-char App Password

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "987654321")


def send_telegram_notification(text: str):
    """Sends a formatted message to your Telegram channel/chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()
    except Exception as e:
        print(f"Failed to dispatch Telegram alert: {e}")


def parse_bazos_email(subject: str, html_body: str):
    """
    Parses incoming Bazoš search agent listings.
    Customize the text-extraction logic below to fit your needs.
    """
    print(f"Extracting updates from email: {subject}")

    # Simple placeholder parser structure:
    # 1. Grab raw links or prices out of html_body (using regex or simple splits)
    # 2. Compile into a human-readable notification text

    notification_msg = (
        f"<b>🔔 New Bazoš Alert!</b>\n"
        f"Subject: {subject}\n\n"
        f"Check your burner inbox or click below to view listings directly."
    )

    # Send it down the line
    send_telegram_notification(notification_msg)


def check_for_alerts():
    print("Poller active: checking burner mailbox for unread alerts...")
    try:
        with MailBox(IMAP_SERVER).login(
            EMAIL_USER, EMAIL_PASSWORD, initial_folder="INBOX"
        ) as mailbox:
            # Fetches unread, sets them read instantly so next run skips them
            for msg in mailbox.fetch(criteria=AND(seen=False), mark_seen=True):
                print(f"Processing unread item: {msg.subject}")

                body_content = msg.text if msg.text else msg.html
                parse_bazos_email(msg.subject, body_content)

    except Exception as e:
        print(f"Mailbox sync execution error: {e}")


# Entry points
def lambda_handler(event, context):
    """AWS Lambda trigger binding hook"""
    check_for_alerts()
    return {"status": "complete"}


if __name__ == "__main__":
    # Local terminal testing runtime execution
    check_for_alerts()
