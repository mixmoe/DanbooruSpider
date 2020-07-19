import asyncio
from random import choice as randChoice
from typing import AsyncIterator, List, NoReturn, Optional, Union

from httpx import URL, AsyncClient, HTTPError

from ..config import VERSION, Config
from ..exceptions import DanbooruException, NetworkException, SpiderException
from ..log import logger
from ..utils import AsyncOpen, HashCreator, Retry, TempFile
from . import models

ImageSpiderConfig = Config["spider"]["images"]


class StoppedException(DanbooruException):
    pass


class ImageSpiderWorker:
    def __init__(
        self,
        queue: Optional[asyncio.Queue] = None,
        *,
        workers: Optional[int] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self._proxy: Optional[str] = proxy or ImageSpiderConfig[
            "proxy"
        ].as_str() or None
        self._workers: int = workers or ImageSpiderConfig["workers"].as_number()
        self._queue: asyncio.Queue = asyncio.Queue(self._workers)
        self._tasks: List[asyncio.Task] = []
        self._running = 0
        self._stopped = False

        if queue is not None:
            self._tasks.append(asyncio.create_task(self._imagesListFetcher(queue)))
        self._tasks.append(asyncio.create_task(self._runningTaskCleaner()))

    async def _imagesListFetcher(self, queue: asyncio.Queue) -> NoReturn:
        while True:
            imagesList: List[models.DanbooruImage] = await queue.get()
            await self.add(imagesList)

    async def _runningTaskCleaner(self) -> NoReturn:
        while True:
            for finishedTask in filter(lambda x: x.done(), self._tasks):
                self._tasks.remove(finishedTask)
            await asyncio.sleep(1)

    @Retry(
        retries=ImageSpiderConfig["retries"]["times"].as_number(),
        delay=ImageSpiderConfig["retries"]["delay"].as_number(),
    )
    async def _imageDownload(
        self, client: AsyncClient, data: models.DanbooruImage,
    ) -> models.ImageDownload:
        while self._running >= self._workers:
            await asyncio.sleep(1)
        self._running += 1

        urlParsed = URL(data.imageURL)
        logger.trace(
            "Start downloading picture "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        tempfile, hashData, totalWrite = TempFile().create(), HashCreator(), 0
        try:
            response = await client.get(
                urlParsed,
                headers={
                    "User-Agent": randChoice(
                        ImageSpiderConfig["user-agents"].get(list)
                        or [f"DanbooruSpider/{VERSION}"]
                    ),
                },
            )
            response.raise_for_status()
            async with AsyncOpen(str(tempfile), "wb") as f:
                async for chunk in response.aiter_bytes():
                    await hashData.update(chunk)
                    totalWrite += await f.write(chunk)
            logger.trace(
                "Finished downloading picture "
                + f"{urlParsed.full_path!r} from {urlParsed.host!r}, "
                + f"total write {totalWrite} bytes."
            )
        except HTTPError as e:
            raise NetworkException(
                "There was an error in the network when processing the picture "
                + f"'{urlParsed}', the reason is: {e}"
            )
        except Exception as e:
            raise SpiderException(
                "There was a unknown error when processing the picture "
                + f"'{urlParsed}', the reason is: {e}"
            )
        finally:
            self._running -= 1
        return models.ImageDownload(
            **{
                "source": str(urlParsed),
                "path": tempfile,
                "size": totalWrite,
                "md5": await hashData.hexdigest(),
                "data": data,
            }
        )

    async def _imageQueuePut(self, images: List[models.DanbooruImage]) -> asyncio.Queue:
        async def customers(client: AsyncClient, data: models.DanbooruImage) -> None:
            result: Union[models.ImageDownload, Exception]
            try:
                result = await self._imageDownload(client, data)
            except Exception as e:
                result = e
            await self._queue.put(result)

        async with AsyncClient(proxies=self._proxy) as client:
            await asyncio.gather(
                *map(lambda data: customers(client, data), images),
                return_exceptions=True,
            )
        return self._queue

    async def add(self, images: List[models.DanbooruImage], wait: bool = True) -> None:
        from ..persistence import Services

        if self._stopped:
            raise StoppedException
        for image in [*images]:
            if not await Services.checkImageExist(image.imageMD5):
                continue
            logger.debug(
                f"Download of picture {image.id} from {image.source!r}"
                + "has been skipped due to hash duplicate."
            )
            images.remove(image)
        task = asyncio.create_task(self._imageQueuePut(images))
        self._tasks.append(task)
        while wait and not task.done():
            await asyncio.sleep(1)
        return

    async def results(self) -> AsyncIterator[models.ImageDownload]:
        while (not self._stopped) or self._queue.empty():
            result: Union[models.ImageDownload, Exception] = await self._queue.get()
            if isinstance(result, Exception):
                try:
                    raise result
                except NetworkException as e:
                    logger.debug(f"A network error occurred while processing: {e}")
                except Exception as e:
                    logger.exception("An unknown error occurred while processing:")
            elif isinstance(result, models.ImageDownload):
                yield result
        return

    async def stop(self, nowait: bool = False):
        self._stopped = True
        if nowait:
            for task in self._tasks:
                if task.done():
                    continue
                task.cancel()
        else:
            while [*filter(lambda x: not x.done(), self._tasks)]:
                await asyncio.sleep(1)
        self._tasks.clear()
