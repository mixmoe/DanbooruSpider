import asyncio
from random import choice as randChoice
from typing import Dict, List, Optional, Union

from httpx import URL, AsyncClient, HTTPError

from ..config import VERSION, Config
from ..exceptions import NetworkException, SpiderException
from ..log import logger
from ..persistence import Persistence, Services
from ..utils import AsyncOpen, HashCreator, Retry, TempFile
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
        self, client: AsyncClient, url: str,
    ) -> models.ImageDownload:
        while self._running >= self._workers:
            await asyncio.sleep(1)
        self._running += 1

        urlParsed = URL(url)
        logger.trace(
            "Start downloading picture "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        tempfile, hashData, totalWrite = TempFile().create(), HashCreator(), 0
        try:
            response = await client.get(
                url,
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
        async with AsyncClient(proxies=self._proxy,) as client:
            results: Dict[str, Union[Exception, models.ImageDownload]] = dict(
                zip(
                    urls,
                    await asyncio.gather(
                        *map(
                            lambda url: self._imageDownload(client=client, url=url),
                            urls,
                        ),
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
        imagesURL: Dict[str, models.DanbooruImage] = {}
        for data in images:
            if await Services.checkImageExist(md5=data.imageMD5):
                logger.debug(
                    f"Skip download of picture {data.id} from {data.source!r} "
                    + f"due to the file md5 {data.imageMD5!r} has been exist in database."
                )
                continue
            imagesURL[data.imageURL] = data
        downloadResults = await self._imageBatchDownload([*imagesURL.keys()])
        results: List[models.ImageDownload] = []
        for url, image in downloadResults.items():
            image.data = imagesURL[url]
            if not Persistence.verify(image):
                logger.debug(
                    f"Image {image.data.id} from {image.data.source!r} download failed "
                    + f"due to the file md5 {image.md5.lower()} didn't "
                    + f"match origin file {image.data.imageMD5.lower()}."
                )
                continue
            results.append(image)
        return results
