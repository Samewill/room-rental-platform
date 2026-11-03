from dataclasses import dataclass
from typing import BinaryIO

import cloudinary
from cloudinary import uploader
from cloudinary.exceptions import Error as CloudinaryError

from app.core.config import get_settings


class PhotoStorageError(Exception):
    pass


class PhotoStorageConfigurationError(PhotoStorageError):
    pass


@dataclass(frozen=True)
class StoredPhoto:
    url: str
    public_id: str


class CloudinaryPhotoStorage:
    FOLDER = "room-rental-platform/listings"

    def _configure(self) -> None:
        settings = get_settings()
        if (
            not settings.cloudinary_cloud_name
            or not settings.cloudinary_api_key
            or settings.cloudinary_api_secret is None
            or not settings.cloudinary_api_secret.get_secret_value().strip()
        ):
            raise PhotoStorageConfigurationError(
                "Cloudinary credentials are not configured.",
            )

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret.get_secret_value(),
            secure=True,
        )

    def upload(self, image: BinaryIO) -> StoredPhoto:
        self._configure()
        try:
            result = uploader.upload(
                image,
                folder=self.FOLDER,
                resource_type="image",
            )
        except CloudinaryError as exc:
            raise PhotoStorageError("Cloudinary upload failed.") from exc

        url = result.get("secure_url")
        public_id = result.get("public_id")
        if not isinstance(url, str) or not isinstance(public_id, str):
            raise PhotoStorageError(
                "Cloudinary returned an incomplete upload result.",
            )

        return StoredPhoto(url=url, public_id=public_id)

    def delete(self, public_id: str) -> None:
        self._configure()
        try:
            result = uploader.destroy(public_id, resource_type="image")
        except CloudinaryError as exc:
            raise PhotoStorageError("Cloudinary cleanup failed.") from exc

        if result.get("result") not in {"ok", "not found"}:
            raise PhotoStorageError("Cloudinary cleanup did not complete.")
