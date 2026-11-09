import unittest
from unittest.mock import Mock, patch

import httpx
from pydantic import SecretStr

from app.services.google_places import (
    GooglePlaces,
    GooglePlacesConfigurationError,
    GooglePlacesLookupError,
)


class GooglePlacesTests(unittest.TestCase):
    @patch("app.services.google_places.get_settings")
    @patch("app.services.google_places.httpx.get")
    def test_get_location_uses_field_mask_and_returns_coordinates(
        self,
        http_get: Mock,
        get_settings: Mock,
    ) -> None:
        get_settings.return_value.google_maps_server_api_key = SecretStr(
            "server-key",
        )
        response = Mock()
        response.json.return_value = {
            "location": {"latitude": -26.2041, "longitude": 28.0473},
        }
        http_get.return_value = response

        result = GooglePlaces().get_location("place/id")

        self.assertEqual(result, (-26.2041, 28.0473))
        http_get.assert_called_once_with(
            "https://places.googleapis.com/v1/places/place%2Fid",
            headers={
                "X-Goog-Api-Key": "server-key",
                "X-Goog-FieldMask": "location",
            },
            timeout=8.0,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("app.services.google_places.get_settings")
    def test_get_location_requires_server_key(self, get_settings: Mock) -> None:
        get_settings.return_value.google_maps_server_api_key = None

        with self.assertRaises(GooglePlacesConfigurationError):
            GooglePlaces().get_location("place-id")

    @patch("app.services.google_places.get_settings")
    @patch("app.services.google_places.httpx.get")
    def test_get_location_raises_on_provider_failure(
        self,
        http_get: Mock,
        get_settings: Mock,
    ) -> None:
        get_settings.return_value.google_maps_server_api_key = SecretStr(
            "server-key",
        )
        http_get.side_effect = httpx.ConnectError(
            "network failure",
            request=httpx.Request(
                "GET",
                "https://places.googleapis.com/v1/places/place-id",
            ),
        )

        with self.assertRaises(GooglePlacesLookupError):
            GooglePlaces().get_location("place-id")


if __name__ == "__main__":
    unittest.main()
