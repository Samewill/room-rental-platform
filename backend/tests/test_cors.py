import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_allows_local_frontend_origin(self) -> None:
        for origin in (
            "http://localhost:5173",
            "http://127.0.0.1:5174",
        ):
            with self.subTest(origin=origin):
                response = self.client.get(
                    "/health",
                    headers={"Origin": origin},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"],
                    origin,
                )

    def test_allows_authorized_preflight_request(self) -> None:
        response = self.client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5173",
        )
        self.assertIn("PATCH", response.headers["access-control-allow-methods"])
        allowed_headers = response.headers["access-control-allow-headers"].lower()
        self.assertIn("authorization", allowed_headers)
        self.assertIn("content-type", allowed_headers)

    def test_allows_authorized_preflight_from_vite_fallback_port(self) -> None:
        response = self.client.options(
            "/api/v1/users/me/contact-requests",
            headers={
                "Origin": "http://127.0.0.1:5174",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5174",
        )
        self.assertIn("GET", response.headers["access-control-allow-methods"])
        self.assertIn(
            "authorization",
            response.headers["access-control-allow-headers"].lower(),
        )

    def test_rejects_unlisted_origin(self) -> None:
        response = self.client.get(
            "/health",
            headers={"Origin": "https://untrusted.example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
