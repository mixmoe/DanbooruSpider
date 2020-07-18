import asyncio
from random import choice as randChoice
from typing import Dict, List, Optional, Union

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
        self._proxy: Optional[str] = proxy or ImageSpiderConfig[
            "proxy"
        ].as_str() or None
        self._workers: int = workers or ImageSpiderConfig["workers"].as_number()
        self._running = 0

    @Retry(
        retries=ImageSpiderConfig["retries"]["times"].as_number(),
        delay=ImageSpiderConfig["retries"]["delay"].as_number(),
    )
    async def _imageDownload(
        self, client: AsyncClient, url: str, temp: Optional[str] = None
    ) -> models.ImageDownload:
        while self._running >= self._workers:
            await asyncio.sleep(1)
        self._running += 1

        urlParsed = URL(url)
        logger.trace(
            "Start downloading picture "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        tempfile, hashData, totalWrite = (
            TempFile(folder=temp).create(),
            HashCreator(),
            0,
        )
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
        async with AsyncClient(
            proxies=self._proxy,
            headers={
                "User-Agent": randChoice(
                    ImageSpiderConfig["user-agents"].get(list)
                    or [f"DanbooruSpider/{VERSION}"]
                ),
            },
        ) as client:
            results: Dict[str, Union[Exception, models.ImageDownload]] = dict(
                zip(
                    urls,
                    await asyncio.gather(
                        *[self._imageDownload(client=client, url=url) for url in urls],
                        return_exceptions=True,
                    ),
                )
            )

        for url, exc in results.items():
            if not isinstance(exc, Exception):
                continue
            try:
                raise exc
            except NetworkException as e:
                logger.debug(f"A network error occurred while processing {url!r}: {e}")
            except Exception as e:
                logger.exception(f"An unknown error occurred while processing {url!r}:")

        return {k: v for k, v in results.items() if isinstance(v, models.ImageDownload)}

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
