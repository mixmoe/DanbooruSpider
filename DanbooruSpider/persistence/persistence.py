import json
from pathlib import Path
from shutil import move as moveFile
from typing import Any, Dict

import aiofiles

from ..spider.models import ImageDownload
from ..utils import SyncToAsync

DATA_PATH = Path(".") / "data" / "downloads"
IMAGE_PATH = DATA_PATH / "images"
HASH_DEPTH = 3

DATA_PATH.mkdir(exist_ok=True)
IMAGE_PATH.mkdir(exist_ok=True)


class Persistence:
    @staticmethod
    def verify(image: ImageDownload) -> bool:
        if (not image.md5) or (not image.data):
            return False
        return image.data.imageMD5.lower() == image.md5.lower()

    @staticmethod
    @SyncToAsync
    def _dump(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)

    @staticmethod
    @SyncToAsync
    def _move(source: str, destination: str) -> None:
        moveFile(source, destination)

    @classmethod
    async def save(cls, image: ImageDownload) -> Path:
        assert image.data
        savePath = IMAGE_PATH / ("/".join(image.md5[:HASH_DEPTH]))
        savePath.mkdir(parents=True, exist_ok=True)
        imagePath = savePath / f"{image.md5}.{image.data.imageExt}"
        metadataPath = savePath / f"{image.md5}.json"
        await cls._move(
            str(image.path), str(imagePath),
        )
        async with aiofiles.open(str(metadataPath), "wt", encoding="utf-8") as f:
            await f.write(await cls._dump(image.data.dict()))
        return imagePath
