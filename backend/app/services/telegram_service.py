import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ADMIN_CHAT_ID)

    @classmethod
    async def send_message(
        cls, 
        text: str, 
        chat_id: str | None = None,
        reply_to_message_id: int | None = None,
        parse_mode: str = "HTML"
    ) -> int | None:
        """
        Envía un mensaje a Telegram y retorna el message_id generado.
        """
        token = settings.TELEGRAM_BOT_TOKEN
        target_chat_id = chat_id or settings.TELEGRAM_ADMIN_CHAT_ID

        if not token or not target_chat_id:
            logger.warning("Telegram Bot no está configurado (falta TELEGRAM_BOT_TOKEN o TELEGRAM_ADMIN_CHAT_ID).")
            return None

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload: dict = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg_id = data.get("result", {}).get("message_id")
                    return msg_id
                else:
                    logger.error("Error al enviar mensaje a Telegram: %s - %s", resp.status_code, resp.text)
                    return None
        except Exception as e:
            logger.exception("Excepción conectando con Telegram API: %s", e)
            return None


telegram_service = TelegramService()
