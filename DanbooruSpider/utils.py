from asyncio import AbstractEventLoop, get_event_loop
from asyncio import sleep as sleepAsync
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial, wraps
from hashlib import md5
from inspect import iscoroutinefunction
from pathlib import Path
from shutil import rmtree
from time import sleep as sleepSync
from time import time
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from .log import logger

TEMP_FILE_DIR = Path(".") / "data" / "temp"

_EXECUTOR = ThreadPoolExecutor()
rmtree(TEMP_FILE_DIR, ignore_errors=True)
TEMP_FILE_DIR.mkdir(exist_ok=True)


class TempFile:
    def __init__(self, *, folder: Optional[str] = None, ext: str = ".tmp") -> None:
        assert ext.startswith(".")
        folderPath = Path(folder or str(TEMP_FILE_DIR))
        self._fullPath = folderPath / f"{uuid4()}{ext}"
        self._fullPath.touch(exist_ok=True)

    def create(self) -> Path:
        return self._fullPath.absolute()

    def clean(self) -> None:
        self._fullPath.rmdir()

    def __enter__(self) -> Path:
        return self.create()

    def __exit__(self, *_) -> None:
        self.clean()


class TempFolder:
    def __init__(self, *, folder: Optional[str] = None) -> None:
        folderPath = Path(folder or str(TEMP_FILE_DIR))
        self._fullPath = folderPath / uuid4().hex
        self._fullPath.mkdir(exist_ok=True)

    def create(self) -> Path:
        return self._fullPath.absolute()

    def clean(self) -> None:
        rmtree(self._fullPath, ignore_errors=True)

    def __enter__(self) -> Path:
        return self.create()

    def __exit__(self, *_) -> None:
        self.clean()


def Timing(func: Callable) -> Callable:
    @wraps(func)
    def syncWrapper(*args, **kwargs) -> Any:
        beginTime = time()
        try:
            return func(*args, **kwargs)
        finally:
            endTime = time()
            logger.trace(
                f"Function {func.__qualname__!r} synchronous operation"
                + f" took {(endTime - beginTime) * 1000:.3f} milliseconds"
            )

    @wraps(func)
    async def asyncWrapper(*args, **kwargs) -> Any:
        beginTime = time()
        try:
            return await func(*args, **kwargs)
        finally:
            endTime = time()
            logger.trace(
                f"Function {func.__qualname__!r} asynchronous operation"
                + f" took {(endTime - beginTime) * 1000:.3f} milliseconds"
            )

    return asyncWrapper if iscoroutinefunction(func) else syncWrapper


def Retry(
    func: Optional[Callable] = None, retries: int = 5, delay: float = 5
) -> Callable:
    if func is None:
        return partial(Retry, retries=retries)

    @Timing
    @wraps(func)
    def syncWrapper(*args, **kwargs) -> Any:
        for i in range(retries):
            try:
                return func(*args, **kwargs)  # type: ignore
            except Exception as e:
                if i == (retries - 1):
                    raise
                logger.trace(
                    f"Error {e!r}{e} occurred during executing sync function "
                    + f"{func.__qualname__!r}, retring ({i}/{retries})."  # type: ignore
                )
            sleepSync(delay)

    @Timing
    @wraps(func)
    async def asyncWrapper(*args, **kwargs) -> Any:
        for i in range(retries):
            try:
                return await func(*args, **kwargs)  # type: ignore
            except Exception as e:
                if i == (retries - 1):
                    raise
                logger.trace(
                    f"Error {e!r}{e} occurred during executing async function "
                    + f"{func.__qualname__!r}, retring ({i}/{retries})."  # type: ignore
                )
            await sleepAsync(delay)

    return asyncWrapper if iscoroutinefunction(func) else syncWrapper


def SyncToAsync(func: Callable) -> Callable[..., Awaitable]:
    @Timing
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        loop: AbstractEventLoop = get_event_loop()
        runner: Callable[[], Any] = lambda: func(*args, **kwargs)
        return await loop.run_in_executor(_EXECUTOR, runner)

    return wrapper


class HashCreator:
    def __init__(self, algorithm: Callable = md5) -> None:
        self._hash = algorithm()

    @SyncToAsync
    def update(self, data: bytes) -> int:
        self._hash.update(data)
        return len(data)

    @SyncToAsync
    def hexdigest(self) -> str:
        return self._hash.hexdigest()


class AsyncTempFolder(TempFolder):
    async def __aenter__(self) -> Path:
        return self.__enter__()

    @SyncToAsync
    def __aexit__(self):
        self.__exit__()
