import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


class WhatsAppProviderError(Exception):
    pass


class WhatsAppCloudAPI:
    def __init__(self) -> None:
        self._settings = get_settings()

    def send_text(self, phone_number: str, content: str) -> str:
        return self._send(
            phone_number,
            {
                "type": "text",
                "text": {"preview_url": False, "body": content},
            },
        )

    def send_template(
        self,
        phone_number: str,
        template_name: str,
        parameter: str,
    ) -> str:
        return self._send(
            phone_number,
            {
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": self._settings.whatsapp_template_language,
                    },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": parameter},
                            ],
                        },
                    ],
                },
            },
        )

    def _send(self, phone_number: str, message: dict[str, object]) -> str:
        access_token = self._settings.whatsapp_access_token
        phone_number_id = self._settings.whatsapp_phone_number_id
        version = self._settings.whatsapp_graph_api_version
        if (
            access_token is None
            or phone_number_id is None
            or not re.fullmatch(r"v\d+\.\d+", version)
        ):
            raise WhatsAppProviderError(
                "WhatsApp Business API is not fully configured.",
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number.lstrip("+"),
            **message,
        }
        request = Request(
            (
                f"https://graph.facebook.com/{version}/"
                f"{phone_number_id}/messages"
            ),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": (
                    f"Bearer {access_token.get_secret_value()}"
                ),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                body = json.loads(response.read())
        except (
            HTTPError,
            URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise WhatsAppProviderError(
                "WhatsApp message could not be delivered.",
            ) from exc

        messages = body.get("messages") if isinstance(body, dict) else None
        if not isinstance(messages, list) or not messages:
            raise WhatsAppProviderError(
                "WhatsApp provider returned no message identifier.",
            )
        provider_id = (
            messages[0].get("id")
            if isinstance(messages[0], dict)
            else None
        )
        if not isinstance(provider_id, str) or not provider_id:
            raise WhatsAppProviderError(
                "WhatsApp provider returned no message identifier.",
            )
        return provider_id
