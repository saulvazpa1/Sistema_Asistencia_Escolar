import requests
from config import TELEGRAM_BOT_TOKEN


class TelegramService:

    def enviar_mensaje(self, chat_id, mensaje):

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        datos = {
            "chat_id": chat_id,
            "text": mensaje
        }

        try:
            respuesta = requests.post(url, data=datos, timeout=10)
            respuesta.raise_for_status()

            return True

        except requests.RequestException as error:
            print("Error al enviar mensaje de Telegram:", error)
            return False