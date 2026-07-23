import json
import os
import re
import urllib.parse
import urllib.request

import requests
from bs4 import BeautifulSoup
from imap_tools import AND, MailBox, MailMessageFlags

# Configuration - Loaded from environment variables safely
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # 16-char App Password

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BAZOS_MAIL = "agent@bazos.cz"


def get_bazos_ad_image(ad_url: str) -> str | None:
    """Fetches the main image URL from a Bazoš listing page."""
    try:
        # User-Agent prevents Bazoš from blocking requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(ad_url, headers=headers, timeout=5)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # OpenGraph meta tag holds the primary listing photo
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image["content"]

            # Fallback: Find first thumbnail image in the main content gallery
            first_img = soup.find("img", class_="flim") or soup.find(
                "img", class_="barvacka"
            )
            if first_img and first_img.get("src"):
                return first_img["src"]
    except Exception as e:
        print(f"Failed to fetch image for {ad_url}: {e}")

    return None


def send_telegram_notification(listings: list[dict[str, str]]) -> None:
    """Sends a formatted message to your Telegram channel/chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    fallback_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for listing in listings:
        notification_msg = (
            f"<b>🔔 Nové Bazoš upozornění!</b>\n"
            f"{listing['title']}\n"
            f"Cena: {listing['price']}\n"
            f"Link: {listing['url']}"
        )
        if listing["photo"]:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": notification_msg,
                "parse_mode": "HTML",
                "photo": get_bazos_ad_image(listing["url"]),
                "disable_web_page_preview": False,
            }
        else:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": notification_msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }
            url = fallback_url

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read()
        except Exception as e:
            print(f"Failed to dispatch Telegram alert: {e}")

    return None


def parse_bazos_email(html_body: str) -> list[dict[str, str]]:
    """
    Parses incoming Bazoš search agent listings.
    Customize the text-extraction logic below to fit your needs.
    """

    soup = BeautifulSoup(html_body, "html.parser")
    listings = []

    for link in soup.find_all("a", href=True):
        url = str(link["href"])

        if "/inzerat/" in url:
            title = link.get_text(strip=True)

            # The line containing the link also contains the price (e.g. "19 000,-")
            parent_text = link.parent.get_text(strip=True)

            # Look for typical Bazoš price patterns (numbers followed by ,-)
            price_match = re.search(r"(\d[\d\s]*,-)", parent_text)
            price = price_match.group(1).strip() if price_match else "N/A"

            listings.append(
                {
                    "title": title,
                    "url": url,
                    "price": price,
                    "photo": get_bazos_ad_image(url),
                }
            )

    return listings


def check_for_alerts():
    print("Poller active: checking burner mailbox for unread alerts...")
    if not (EMAIL_USER or EMAIL_PASSWORD):
        raise EnvironmentError("Missing required environment variables!")
    try:
        with MailBox(IMAP_SERVER).login(
            EMAIL_USER, EMAIL_PASSWORD, initial_folder="INBOX"
        ) as mailbox:
            # Fetch unread from Bazoš and process
            emails = []
            for msg in mailbox.fetch(
                criteria=AND(seen=False, from_=BAZOS_MAIL), mark_seen=False
            ):
                print(f"Processing unread email: {msg.subject}")
                emails.append(msg)
            return emails

    except Exception as e:
        print(f"Mailbox sync execution error: {e}")


def main():
    if not (EMAIL_USER or EMAIL_PASSWORD or TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN):
        raise OSError("Missing required environment variables!")
    emails = check_for_alerts()
    if emails is None:
        print("No new emails found!")
    else:
        number_of_emails = len(emails)
        print(f"Extracting listings from {number_of_emails} found emails!")
        for email in emails:
            listings = parse_bazos_email(email.html)
            send_telegram_notification(listings)

        # Finally mark the processed mails as read - keeps the entire notification check atomic
        uids_to_mark = [msg.uid for msg in emails]
        if uids_to_mark:
            with MailBox(IMAP_SERVER).login(EMAIL_USER, EMAIL_PASSWORD) as mailbox:
                mailbox.flag(uids_to_mark, MailMessageFlags.SEEN, True)
                print(f"Marked {number_of_emails} email(s) as read.")


# Entry points
def lambda_handler(event, context):
    """AWS Lambda trigger binding hook"""
    main()
    return {"status": "complete"}


if __name__ == "__main__":
    main()
