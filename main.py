import asyncio

from DanbooruSpider.config import Config
from DanbooruSpider.persistence import Persistence, Services
from DanbooruSpider.spider.image import ImageSpiderWorker
from DanbooruSpider.spider.list import ListSpiderManager
from DanbooruSpider.spider.list.worker import DanbooruImageList_T

SpidersConfig = Config["spider"]["lists"]["spiders"]


async def customer(queue: asyncio.Queue):
    worker = ImageSpiderWorker()
    while True:
        listData: DanbooruImageList_T = await queue.get()
        downloaded = await worker.run(listData)
        for i in downloaded:
            i.path = await Persistence.save(i)
            await Services.createImage(i)


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
