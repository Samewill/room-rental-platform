import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from cloudinary.exceptions import Error as CloudinaryError
from pydantic import SecretStr

from app.services.photo_storage import (
    CloudinaryPhotoStorage,
    PhotoStorageConfigurationError,
    PhotoStorageError,
    StoredPhoto,
)


class CloudinaryPhotoStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = CloudinaryPhotoStorage()
        self.settings = SimpleNamespace(
            cloudinary_cloud_name="test-cloud",
            cloudinary_api_key="test-key",
            cloudinary_api_secret=SecretStr("test-secret"),
        )

    def test_upload_requires_cloudinary_configuration(self) -> None:
        settings = SimpleNamespace(
            cloudinary_cloud_name=None,
            cloudinary_api_key=None,
            cloudinary_api_secret=None,
        )

        with (
            patch("app.services.photo_storage.get_settings", return_value=settings),
            patch("app.services.photo_storage.uploader.upload") as upload,
            self.assertRaises(PhotoStorageConfigurationError),
        ):
            self.storage.upload(BytesIO(b"image"))

        upload.assert_not_called()

    def test_upload_configures_cloudinary_and_returns_secure_photo(self) -> None:
        with (
            patch(
                "app.services.photo_storage.get_settings",
                return_value=self.settings,
            ),
            patch("app.services.photo_storage.cloudinary.config") as configure,
            patch(
                "app.services.photo_storage.uploader.upload",
                return_value={
                    "secure_url": "https://res.cloudinary.com/test/room.png",
                    "public_id": "listings/room",
                },
            ) as upload,
        ):
            result = self.storage.upload(BytesIO(b"image"))

        self.assertEqual(
            result,
            StoredPhoto(
                url="https://res.cloudinary.com/test/room.png",
                public_id="listings/room",
            ),
        )
        configure.assert_called_once_with(
            cloud_name="test-cloud",
            api_key="test-key",
            api_secret="test-secret",
            secure=True,
        )
        upload.assert_called_once()

    def test_upload_translates_cloudinary_errors(self) -> None:
        with (
            patch(
                "app.services.photo_storage.get_settings",
                return_value=self.settings,
            ),
            patch("app.services.photo_storage.cloudinary.config"),
            patch(
                "app.services.photo_storage.uploader.upload",
                side_effect=CloudinaryError("upload failed"),
            ),
            self.assertRaises(PhotoStorageError),
        ):
            self.storage.upload(BytesIO(b"image"))

    def test_delete_raises_when_cloudinary_does_not_confirm_cleanup(self) -> None:
        with (
            patch(
                "app.services.photo_storage.get_settings",
                return_value=self.settings,
            ),
            patch("app.services.photo_storage.cloudinary.config"),
            patch(
                "app.services.photo_storage.uploader.destroy",
                return_value={"result": "error"},
            ),
            self.assertRaises(PhotoStorageError),
        ):
            self.storage.delete("listings/room")


if __name__ == "__main__":
    unittest.main()
