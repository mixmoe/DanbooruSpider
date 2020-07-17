import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
from httpx import URL, AsyncClient, HTTPError

from ..exceptions import NetworkException, SpiderException
from ..log import logger
from ..utils import TempFile


class SpiderWorker:
    def __init__(
        self, address: Union[str, URL], workers: int = 16, proxy: Optional[str] = None
    ) -> None:
        addressParsed = URL(address)
        self._referer = f"{addressParsed.scheme}://{addressParsed.host}"
        self._proxy = proxy
        self._workers = workers
        self._running = 0

    async def _imageDownload(self, client: AsyncClient, url: str) -> Path:
        urlParsed = URL(url)
        logger.trace(
            "Start downloading picture "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        while self._running >= self._workers:
            await asyncio.sleep(1)
        self._running += 1
        try:
            response = await client.get(url)
            response.raise_for_status()
            with TempFile(keep=True) as tmpFileName, aiofiles.open(
                str(tmpFileName), "wb"
            ) as f:
                totalWrite = 0
                async for chunk in response.aiter_bytes():
                    totalWrite += f.write(chunk)
            logger.trace(
                "Finished downloading picture "
                + f"{urlParsed.full_path!r} from {urlParsed.host!r}, "
                + f"total write {totalWrite} bytes."
            )
            return tmpFileName
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

    async def _imageBatchDownload(self, urls: List[str]) -> Dict[str, Path]:
        tasks: Dict[str, asyncio.Task] = {}
        async with AsyncClient(
            proxies=self._proxy,
            headers={
                "Referer": self._referer,
                "User-Agent": f"DanbooruSpider/0.0.1 {datetime.now()}",
            },
        ) as client:
            for url in urls:
                coroutine = self._imageDownload(client=client, url=url)
                tasks[url] = asyncio.create_task(coroutine)

            while [*filter(lambda t: not t.done(), tasks.values())]:
                await asyncio.sleep(0)

        result: Dict[str, Path] = {}
        for url, task in tasks.items():
            try:
                result[url] = task.result()
            except NetworkException as e:
                logger.debug(f"A network error occurred in task {task}: {e}")
            except Exception:
                logger.exception(f"A unknown error occurred in task {task}:")
        return result

    async def fetchList(self, params: Dict[str, Any]):
        pass
