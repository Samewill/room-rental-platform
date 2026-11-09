import logging
import math
from urllib.parse import quote

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class GooglePlacesError(Exception):
    pass


class GooglePlacesConfigurationError(GooglePlacesError):
    pass


class GooglePlacesLookupError(GooglePlacesError):
    pass


class GooglePlaces:
    REQUEST_TIMEOUT_SECONDS = 8.0
    PLACES_API_BASE_URL = "https://places.googleapis.com/v1/places/"

    def get_location(self, place_id: str) -> tuple[float, float]:
        settings = get_settings()
        configured_key = settings.google_maps_server_api_key
        api_key = (
            configured_key.get_secret_value().strip()
            if configured_key is not None
            else ""
        )
        if not api_key:
            raise GooglePlacesConfigurationError(
                "Google Places server API key is not configured.",
            )

        try:
            response = httpx.get(
                f"{self.PLACES_API_BASE_URL}{quote(place_id, safe='')}",
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "location",
                },
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            location = payload["location"]
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Google Places location lookup failed")
            raise GooglePlacesLookupError(
                "Google Places could not resolve the selected location.",
            ) from exc

        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise GooglePlacesLookupError(
                "Google Places returned an invalid location.",
            )

        return latitude, longitude
