import asyncio
from typing import List, Optional

from ..exceptions import DatabaseException
from ..log import logger
from ..spider.models import ImageDownload
from . import database
from .database import models


class DatabaseServices:
    pictures = database.Pictures()
    tags = database.Tags()
    tagsrelations = database.TagsRelation()

    @classmethod
    async def checkImageExist(cls, md5: str) -> Optional[models.PicturesRead]:
        try:
            return await cls.pictures.read(md5=md5)
        except DatabaseException:
            return None

    @classmethod
    async def createImage(cls, data: ImageDownload) -> None:
        assert data.data is not None
        if await cls.checkImageExist(data.md5):
            return
        pictureData: models.PicturesRead = await cls.pictures.create(
            models.PicturesCreate(
                **{
                    "md5": data.data.imageMD5,
                    "locale_path": str(data.path),
                    "rating": data.data.rating.lower(),
                    "source": data.data.source,
                    "source_id": data.data.id,
                    "source_url": data.data.imageURL,
                }
            )
        )
        await cls.tags.create(
            [*map(lambda x: models.TagsCreate(**{"name": x}), data.data.tags)]
        )
        tagsData: List[models.TagsRead] = await asyncio.gather(
            *map(lambda x: cls.tags.read(name=x), data.data.tags)
        )
        await cls.tagsrelations.create(
            [
                *map(
                    lambda x: models.TagsRelationCreate(
                        **{"pid": pictureData.pid, "tid": x}
                    ),
                    [i.tid for i in tagsData],
                )
            ]
        )
        logger.trace(f"Data of image {data.data!r} has been stored to database.")
