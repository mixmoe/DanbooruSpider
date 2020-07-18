import asyncio
from itertools import count
from random import choice as randChoice
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from httpx import URL, AsyncClient, HTTPError

from ...config import VERSION, Config
from ...exceptions import NetworkException, NotImplementedException, SpiderException
from ...log import logger
from ...utils import Retry
from .. import models

ListSpiderConfig = Config["spider"]["list"]
APIResult_T = Union[Dict[str, Any], List[Dict[str, Any]]]
DanbooruImageList_T = List[models.DanbooruImage]


class ListSpiderWorker:
    site: str = ""

    def __init__(self, **kwargs) -> None:
        pass

    @Retry(
        retries=ListSpiderConfig["times"].as_number(),
        delay=ListSpiderConfig["delay"].as_number(),
    )
    async def _listDownload(self, client: AsyncClient, url: str) -> APIResult_T:
        urlParsed = URL(url)
        logger.trace(
            "Start downloading list "
            + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
        )
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": randChoice(
                        ListSpiderConfig["user-agents"].get(List[str])
                        or [f"DanbooruSpider/{VERSION}"]
                    )
                },
            )
            response.raise_for_status()
            data: APIResult_T = response.json()
            logger.trace(
                "Finished downloading list "
                + f"{urlParsed.full_path!r} from {urlParsed.host!r}."
            )
        except HTTPError as e:
            raise NetworkException(
                "There was an error in the network when processing the list "
                + f"{url!r}, the reason is: {e}"
            )
        except Exception as e:
            raise SpiderException(
                "There was a unknown error when processing the list "
                + f"{url!r}, the reason is: {e}"
            )
        return data

    async def parse(self, data: APIResult_T) -> DanbooruImageList_T:
        raise NotImplementedException

    async def fetch(self, page: int, size: int) -> APIResult_T:
        raise NotImplementedException

    async def run(
        self, begin: int = 0, end: Optional[int] = None, size: Optional[int] = None
    ) -> AsyncIterator[DanbooruImageList_T]:
        size = size or ListSpiderConfig["size"].as_number()
        end = end or ListSpiderConfig["max-page"].as_number()
        for pagenumber in count(begin):
            if pagenumber >= end:
                break
            try:
                result: DanbooruImageList_T = await self.parse(
                    await self.fetch(pagenumber, size=size)
                )
                if not result:
                    break
                yield result
            except NetworkException as e:
                logger.warning(
                    f"A network error {e} occurred during fetching list from {self.site} page {pagenumber}."
                )
            except Exception as e:
                logger.exception(
                    f"An unknown error {e} occurred during fetching list from {self.site} page {pagenumber}:"
                )
        return
