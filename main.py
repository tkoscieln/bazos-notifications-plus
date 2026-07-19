import functions_framework
import re
import requests
from bs4 import BeautifulSoup
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def get_bazos_image(url):
    try:
        # User-Agent makes the request look like a standard web browser instead of a script
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Bazos uses classes like 'ilustrace' or 'flimg' for the main listing images
            img_tag = soup.find("img", class_="ilustrace") or soup.find(
                "img", class_="flimg"
            )

            if img_tag and img_tag.get("src"):
                return img_tag["src"]
    except Exception as e:
        print(f"Failed to scrape image: {e}")
    return None


def send_telegram_notification(text, photo_url=None):
    if photo_url:
        # Telegram natively accepts a web URL for the photo parameter
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo_url,
            "caption": text,
            "parse_mode": "Markdown",
        }
    else:
        # Fallback to standard text message if no image was found
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}

    requests.post(url, json=payload)


@functions_framework.http
def handle_email_webhook(request):
    request_json = request.get_json(silent=True)

    if request_json and "text" in request_json:
        email_body = request_json["text"]

        # Pull out hyperlinks from the email body
        links = re.findall(r"(https?://[^\s]+)", email_body)
        bazos_links = [l for l in links if "bazos.cz" in l]

        if bazos_links:
            target_url = bazos_links[0]

            # 1. Grab the image URL from the live listing page
            img_url = get_bazos_image(target_url)

            # 2. Build a clean markdown message format
            message_text = (
                f"🔥 *Nový inzerát na Bazoši!*\n\n[Otevřít inzerát]({target_url})"
            )

            # 3. Dispatch to Telegram
            send_telegram_notification(message_text, img_url)
            return "Notification sent successfully", 200

    return "No valid link or body payload found", 200
