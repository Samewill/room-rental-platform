import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.whatsapp import get_whatsapp_service
from app.main import app
from app.models.user import User


class WhatsAppEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app
        self.service = Mock()
        self.user = User(user_id=8)
        self.app.dependency_overrides[get_whatsapp_service] = (
            lambda: self.service
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_status_response_does_not_expose_number(self) -> None:
        self.service.status_for_user.return_value = True

        response = self.client.get("/api/v1/users/me/whatsapp")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": True})

    def test_verification_request_does_not_return_number_or_code(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/whatsapp/verification",
            json={
                "phone_number": "+27123456789",
                "consent": True,
            },
        )

        self.assertEqual(response.status_code, 202)
        self.assertNotIn("+27123456789", response.text)
        self.assertNotIn("code", response.text.casefold())
        self.service.start_verification.assert_called_once_with(
            8,
            "+27123456789",
        )

    def test_verification_requires_explicit_consent(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/whatsapp/verification",
            json={
                "phone_number": "+27123456789",
                "consent": False,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.service.start_verification.assert_not_called()

    def test_validation_error_does_not_echo_submitted_number(self) -> None:
        response = self.client.post(
            "/api/v1/users/me/whatsapp/verification",
            json={
                "phone_number": "07123456789",
                "consent": True,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertNotIn("07123456789", response.text)

    def test_webhook_challenge_requires_expected_token(self) -> None:
        self.service.verify_webhook_challenge.return_value = True

        response = self.client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "expected",
                "hub.challenge": "challenge-value",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "challenge-value")
        self.service.verify_webhook_challenge.assert_called_once_with(
            "subscribe",
            "expected",
        )

    def test_webhook_rejects_invalid_signature(self) -> None:
        self.service.verify_webhook_signature.return_value = False

        response = self.client.post(
            "/api/v1/webhooks/whatsapp",
            content=b'{"entry":[]}',
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )

        self.assertEqual(response.status_code, 403)
        self.service.receive_webhook.assert_not_called()

    def test_verified_webhook_dispatches_payload(self) -> None:
        self.service.verify_webhook_signature.return_value = True
        payload = {"entry": []}

        response = self.client.post(
            "/api/v1/webhooks/whatsapp",
            json=payload,
            headers={"X-Hub-Signature-256": "sha256=valid"},
        )

        self.assertEqual(response.status_code, 200)
        self.service.receive_webhook.assert_called_once_with(payload)


if __name__ == "__main__":
    unittest.main()
