import asyncio
from datetime import datetime
from random import choice as randChoice
from typing import Dict, List, Optional

import aiofiles
from httpx import URL, AsyncClient, HTTPError

from ..config import VERSION, Config
from ..exceptions import NetworkException, SpiderException
from ..log import logger
from ..utils import HashCreator, Retry, TempFile
from . import models

ImageSpiderConfig = Config["spider"]["images"]


class ImageSpiderWorker:
    def __init__(
        self, workers: Optional[int] = None, proxy: Optional[str] = None,
    ) -> None:
        self._proxy: str = proxy or ImageSpiderConfig["proxy"].as_str()
        self._workers: int = workers or ImageSpiderConfig["workers"].as_number()
        self._running = 0

    @Retry(
        retries=ImageSpiderConfig["retries"]["times"].as_number(),
        delay=ImageSpiderConfig["retries"]["delay"].as_number(),
    )
    async def _imageDownload(
        self, client: AsyncClient, url: str
    ) -> models.ImageDownload:
        urlParsed = URL(url)
        logger.trace(
            "Start downloading picture "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        while self._running >= self._workers:
            await asyncio.sleep(1)
        self._running += 1
        tempfile = TempFile().create()
        totalWrite = 0
        hashData = HashCreator()
        try:
            response = await client.get(url)
            response.raise_for_status()
            async with aiofiles.open(str(tempfile), "wb") as f:
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
                + f"{url!r}, the reason is: {e}"
            )
        except Exception as e:
            raise SpiderException(
                "There was a unknown error when processing the picture "
                + f"{url!r}, the reason is: {e}"
            )
        finally:
            self._running -= 1
        return models.ImageDownload(
            **{
                "source": url,
                "path": tempfile,
                "size": totalWrite,
                "md5": await hashData.hexdigest(),
            }
        )

    async def _imageBatchDownload(
        self, urls: List[str]
    ) -> Dict[str, models.ImageDownload]:
        tasks: Dict[str, asyncio.Task] = {}
        async with AsyncClient(
            proxies=self._proxy,
            headers={
                "User-Agent": randChoice(
                    ImageSpiderConfig["user-agents"].get(List[str])
                    or [f"DanbooruSpider/{VERSION}"]
                ),
            },
        ) as client:
            for url in urls:
                coroutine = self._imageDownload(client=client, url=url)
                tasks[url] = asyncio.create_task(coroutine)

            while [*filter(lambda t: not t.done(), tasks.values())]:
                await asyncio.sleep(0)

        result: Dict[str, models.ImageDownload] = {}
        for url, task in tasks.items():
            try:
                result[url] = task.result()
            except NetworkException as e:
                logger.debug(f"A network error occurred in task {task}: {e}")
            except Exception:
                logger.exception(f"A unknown error occurred in task {task}:")
        return result

    async def run(
        self, images: List[models.DanbooruImage]
    ) -> List[models.ImageDownload]:
        imagesURL: Dict[str, models.DanbooruImage] = {i.imageURL: i for i in images}
        downloadResults = await self._imageBatchDownload([*imagesURL.keys()])
        results: List[models.ImageDownload] = []
        for url, image in downloadResults.items():
            image.data = imagesURL[url]
            results.append(image)
        return [*results]
