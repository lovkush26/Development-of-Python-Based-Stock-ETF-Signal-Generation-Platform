"""
alerting/notifier.py — Multi-channel, multi-user alert delivery.
Users are loaded from the persistent database (survive restarts).
"""

from config.settings import get_settings
from utils.logger import log
from utils.user_store import get_all_users, log_alert, init_user_tables

settings = get_settings()

# Initialize tables on import
init_user_tables()


class AlertNotifier:
    """Sends alerts to all DB-registered users across Slack, Email, and SMS."""

    def send(
        self,
        message: str,
        subject: str = "AlphaSignal Alert",
        channels: list = None,
        to_phone: str = None,
        to_email: str = None,
    ):
        channels = channels or self._configured_channels()
        for channel in channels:
            try:
                if channel == "sms":
                    self._send_sms(message, to_number=to_phone)
                elif channel == "email":
                    self._send_email(subject, message, to_email=to_email)
                elif channel == "slack":
                    self._send_slack(message)
            except Exception as e:
                log.error(f"Alert delivery failed [{channel}]: {e}")

    def send_signal_alert(
        self,
        ticker: str,
        signal: str,
        confidence: float,
        price: float,
    ):
        """Send signal alert to ALL users registered in the database."""
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
        msg = (
            f"{emoji} {ticker} — {signal} signal\n"
            f"Confidence: {confidence*100:.1f}%\n"
            f"Price: ${price:.2f}\n"
            f"Platform: AlphaSignal ML Engine"
        )
        subject = f"AlphaSignal: {ticker} {signal}"

        users = get_all_users()
        sent_count = 0

        for user in users:
            # Check confidence threshold
            if confidence < user.get("min_confidence", 0):
                continue

            # Check ticker filter
            allowed = user.get("tickers")
            if allowed and ticker not in allowed:
                continue

            # Deliver on each channel
            for channel in user.get("channels", []):
                try:
                    if channel == "sms" and user.get("phone"):
                        self._send_sms(msg, to_number=user["phone"])
                        log_alert(user["name"], ticker, signal, confidence, price, "sms", msg)
                        log.info(f"SMS sent to {user['name']}")

                    elif channel == "email" and user.get("email"):
                        self._send_email(subject, msg, to_email=user["email"])
                        log_alert(user["name"], ticker, signal, confidence, price, "email", msg)
                        log.info(f"Email sent to {user['name']}")

                    elif channel == "slack":
                        self._send_slack(msg)
                        log_alert(user["name"], ticker, signal, confidence, price, "slack", msg)

                except Exception as e:
                    log.error(f"Failed to alert {user['name']} via {channel}: {e}")

            sent_count += 1

        log.info(f"Signal alert sent to {sent_count}/{len(users)} users")

    def send_to_all(self, message: str, subject: str = "AlphaSignal Alert"):
        """Broadcast to all users on all their channels."""
        users = get_all_users()
        for user in users:
            for channel in user.get("channels", []):
                try:
                    if channel == "sms" and user.get("phone"):
                        self._send_sms(message, to_number=user["phone"])
                    elif channel == "email" and user.get("email"):
                        self._send_email(subject, message, to_email=user["email"])
                    elif channel == "slack":
                        self._send_slack(message)
                except Exception as e:
                    log.error(f"Broadcast failed for {user['name']} [{channel}]: {e}")

    def list_users(self) -> list:
        return get_all_users()

    # ── Slack ─────────────────────────────────────────────────────────────────
    def _send_slack(self, message: str):
        if not settings.slack_bot_token:
            log.debug("Slack not configured.")
            return
        from slack_sdk import WebClient
        WebClient(token=settings.slack_bot_token).chat_postMessage(
            channel=settings.slack_channel, text=message
        )
        log.info(f"Slack alert sent")

    # ── Email ─────────────────────────────────────────────────────────────────
    def _send_email(self, subject: str, body: str, to_email: str = None):
        to_email = to_email or settings.alert_to_email
        if not settings.sendgrid_api_key or not to_email:
            log.debug("SendGrid not configured.")
            return
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        msg = Mail(
            from_email=settings.alert_from_email,
            to_emails=to_email,
            subject=subject,
            html_content=f"<pre style='font-family:monospace;font-size:14px'>{body}</pre>",
        )
        SendGridAPIClient(settings.sendgrid_api_key).send(msg)
        log.info(f"Email sent to {to_email}")

    # ── SMS ───────────────────────────────────────────────────────────────────
    def _send_sms(self, message: str, to_number: str = None):
        to_number = to_number or settings.alert_to_number
        if not settings.twilio_account_sid or not to_number:
            log.debug("Twilio not configured.")
            return
        from twilio.rest import Client
        Client(settings.twilio_account_sid, settings.twilio_auth_token).messages.create(
            body=message[:160],
            from_=settings.twilio_from_number,
            to=to_number,
        )
        log.info(f"SMS sent to ...{to_number[-4:]}")

    def _configured_channels(self) -> list:
        channels = []
        if settings.slack_bot_token:   channels.append("slack")
        if settings.sendgrid_api_key:  channels.append("email")
        if settings.twilio_account_sid: channels.append("sms")
        return channels