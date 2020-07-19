import asyncio
from typing import NoReturn

from DanbooruSpider.config import Config
from DanbooruSpider.log import logger
from DanbooruSpider.persistence import Persistence, Services
from DanbooruSpider.spider import ImageSpiderWorker, ListSpiderManager

SpidersConfig = Config["spider"]["lists"]["spiders"]


async def customer(queue: asyncio.Queue) -> None:
    worker = ImageSpiderWorker(queue)
    async for image in worker.results():
        if not Persistence.verify(image):
            logger.warning(
                f"Hash verify of image {image.source!r} failed. "
                + f"({image.md5} did not match {image.data.imageMD5})"
            )
            continue
        image.path = await Persistence.save(image)
        await Services.createImage(image)


async def main():
    for i in SpidersConfig:
        ListSpiderManager.instance(
            i["impl"].as_str(), i["name"].as_str(), i["config"].get(dict)
        )
        queue = await ListSpiderManager.run(name=i["name"].as_str())
        asyncio.create_task(customer(queue))
    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
