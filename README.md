[![Deploy to AWS Lambda](https://github.com/tkoscieln/bazos-notifications-plus/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/tkoscieln/bazos-notifications-plus/actions/workflows/deploy.yml) [![License: GPL v3](https://img.shields.io/badge/license-%20%20GNU%20GPLv3%20-green)](https://gnu.org)

# Bazoš.cz Notifications Plus

🇬🇧 A small application for AWS Lambda that improves [bazos.cz](https://www.bazos.cz/) search-agent email alerts. Bazoš's built-in service sends basic emails containing listing links and prices. This app checks a mailbox for those alerts, extracts the listings, looks up their preview images, and sends formatted notifications to [Telegram](https://telegram.org/).

🇨🇿 Toto je malá aplikace pro AWS Lambda, jejímž cílem je vylepšit způsob, jakým [bazos.cz](https://www.bazos.cz/) odesílá upozornění na inzeráty. Bazoš má integrovaného hlídacího psa, ale jde o jednoduché e-mailové upozornění obsahující pouze URL a cenu. Tato aplikace ji rozšiřuje o náhledový obrázek, lepší formátování a odesílání notifikací přes [Telegram](https://telegram.org/).

## How it works

1. Create a Bazoš search agent and have its alerts delivered to a mailbox you can access over IMAP. (*Note: You can use throwaway mailbox*)
2. When invoked, the app checks that mailbox for unread messages from `agent@bazos.cz`.
3. It extracts listing titles, prices, and links from each alert, then looks up listing images.
4. It sends each listing to the configured Telegram chat. If an image is unavailable, it sends a text message instead.
5. After processing, it marks the alert emails as read so they are not processed again.

The app does not poll continuously by itself. In AWS, configure a scheduled EventBridge rule to invoke the Lambda function at the interval you want.

## Notification format

The message includes the listing title, price, and link. When a listing image is available, it is sent as a Telegram photo caption; otherwise, it is sent as a text message. The current message heading is in Czech:

```text
🔔 Nové Bazoš upozornění!
Titul
Cena: 19 000,-
Link: https://www.bazos.cz/inzerat/...
```

## Setup

### Prerequisites

- Python 3.14 and [uv](https://docs.astral.sh/uv/) for local development.
- A mailbox that supports IMAP. Gmail users need IMAP enabled and should use a Google App Password (not their normal account password) when two-step verification is enabled.
- *Note: You can use throwaway mailbox*
- A Telegram bot and the ID of the chat or channel where it should post. Create a bot through [@BotFather](https://t.me/BotFather), then start a conversation with it (or add it to your channel and grant it permission to post).
- For AWS deployment: an AWS account, Docker-compatible Lambda container support, and an ECR repository.

### Configuration

Set these environment variables for local runs and in the Lambda function configuration:

| Variable | Required | Description |
| --- | --- | --- |
| `EMAIL_USER` | Yes | IMAP mailbox username, usually the full email address. |
| `EMAIL_PASSWORD` | Yes | Mailbox password or provider-specific app password. |
| `TELEGRAM_BOT_TOKEN` | Yes | Token issued by BotFather. Keep it secret. |
| `TELEGRAM_CHAT_ID` | Yes | Telegram user, group, or channel ID to receive notifications. |
| `IMAP_SERVER` | No | IMAP server hostname. Defaults to `imap.gmail.com`. |

Do not commit credentials or add them to source control. Use local environment variables or an ignored `.env` file for development, and configure secrets through AWS Lambda's environment-variable settings for deployment. Anyone with the Telegram bot token or mailbox credentials can use them; rotate credentials if they are exposed.

### Run locally

From the project directory, install the locked dependencies and set the configuration:

```bash
uv sync --frozen
export EMAIL_USER="your-mailbox@example.com"
export EMAIL_PASSWORD="your-app-password"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
# Optional; defaults to imap.gmail.com
export IMAP_SERVER="imap.gmail.com"
uv run python main.py
```

Running the command checks and processes unread Bazoš alert emails once. Run it again, or schedule it externally, to check for later alerts.

### AWS Lambda deployment

The included `Dockerfile` builds a Python 3.14 Lambda container image and configures `main.lambda_handler` as its handler. The GitHub Actions deployment workflow targets AWS region `eu-central-1`, ECR repository `bazos-bot`, and Lambda function `bazos-email-bot`; create these resources in that region or update `.github/workflows/deploy.yml` to match your own names.

1. Create an ECR repository and a Lambda function that uses a container image from that repository. Configure the function for the `linux/amd64` architecture, which is the architecture built by the workflow.
2. Add the five configuration variables above (including `IMAP_SERVER` if you use a non-Gmail provider) to the Lambda function's environment variables.
3. Configure an EventBridge scheduled rule to invoke the Lambda function regularly. Choose an interval that suits your needs and the mailbox provider's limits.
4. In the GitHub repository, add these Actions secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
5. Give those AWS credentials permission to authenticate to ECR and push images, and to update the target Lambda function's code. The workflow logs in to ECR, builds the image, and updates the function when code is pushed to `main`. Pull requests build the image without pushing or deploying it.

The Lambda function also needs permission for EventBridge to invoke it. Set an appropriate Lambda timeout for mailbox access and Telegram requests; increase it if processing multiple alerts takes longer.

## Development

Dependencies are declared in `pyproject.toml` and pinned by `uv.lock`. To run the formatter check used by CI:

```bash
uv run black --check .
```

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
