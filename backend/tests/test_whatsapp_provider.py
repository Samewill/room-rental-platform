import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import URLError

from pydantic import SecretStr

from app.services.whatsapp_provider import (
    WhatsAppCloudAPI,
    WhatsAppProviderError,
)


class WhatsAppProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = SimpleNamespace(
            whatsapp_access_token=SecretStr("private-access-token"),
            whatsapp_phone_number_id="business-phone-id",
            whatsapp_graph_api_version="v23.0",
        )

    def test_sends_through_platform_business_number(self) -> None:
        response = Mock()
        response.read.return_value = b'{"messages":[{"id":"wamid.123"}]}'
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)

        with (
            patch(
                "app.services.whatsapp_provider.get_settings",
                return_value=self.settings,
            ),
            patch(
                "app.services.whatsapp_provider.urlopen",
                return_value=context,
            ) as urlopen,
        ):
            provider = WhatsAppCloudAPI()
            message_id = provider.send_text(
                "+27123456789",
                "Ref ABCDEFGH: Hello",
            )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(message_id, "wamid.123")
        self.assertEqual(
            request.full_url,
            "https://graph.facebook.com/v23.0/"
            "business-phone-id/messages",
        )
        self.assertEqual(payload["to"], "27123456789")
        self.assertEqual(payload["type"], "text")
        self.assertEqual(
            payload["text"]["body"],
            "Ref ABCDEFGH: Hello",
        )
        self.assertEqual(
            request.headers["Authorization"],
            "Bearer private-access-token",
        )

    def test_provider_errors_do_not_include_phone_numbers(self) -> None:
        with (
            patch(
                "app.services.whatsapp_provider.get_settings",
                return_value=self.settings,
            ),
            patch(
                "app.services.whatsapp_provider.urlopen",
                side_effect=URLError("connection failed"),
            ),
        ):
            with self.assertRaises(WhatsAppProviderError) as error:
                WhatsAppCloudAPI().send_text(
                    "+27123456789",
                    "A message",
                )

        self.assertNotIn("+27123456789", str(error.exception))


if __name__ == "__main__":
    unittest.main()
