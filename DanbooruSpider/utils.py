from asyncio import AbstractEventLoop, get_event_loop
from asyncio import sleep as sleepAsync
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial, wraps
from hashlib import md5
from inspect import iscoroutinefunction
from pathlib import Path
from random import randint
from shutil import rmtree
from time import sleep as sleepSync
from time import time
from typing import Any, Awaitable, Callable, Optional, Union
from uuid import uuid4

import aiofiles
from aiofiles.base import AiofilesContextManager

from .log import logger

TEMP_FILE_DIR = Path(".") / "data" / "temp"

_EXECUTOR = ThreadPoolExecutor()
rmtree(TEMP_FILE_DIR, ignore_errors=True)
TEMP_FILE_DIR.mkdir(exist_ok=True)

AsyncFunc_T = Callable[..., Awaitable[Any]]


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
        assert func
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == (retries - 1):
                    raise
                logger.trace(
                    f"Error {e!r}{e} occurred during executing sync function "
                    + f"{func.__qualname__!r}, retring ({i}/{retries})."
                )
            sleepSync(delay if delay > 0 else randint(0, 10))

    @Timing
    @wraps(func)
    async def asyncWrapper(*args, **kwargs) -> Any:
        assert func
        for i in range(retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if i == (retries - 1):
                    raise
                logger.trace(
                    f"Error {e!r}{e} occurred during executing async function "
                    + f"{func.__qualname__!r}, retring ({i}/{retries})."
                )
            await sleepAsync(delay if delay > 0 else randint(0, 10))

    return asyncWrapper if iscoroutinefunction(func) else syncWrapper


def SyncToAsync(
    func: Optional[Callable] = None,
    *,
    loop: Optional[AbstractEventLoop] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> AsyncFunc_T:
    if func is None:
        return partial(SyncToAsync, executor=executor)  # type: ignore

    @Timing
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        assert func
        eventLoop: AbstractEventLoop = loop or get_event_loop()
        runner: Callable[[], Any] = lambda: func(*args, **kwargs)  # type: ignore
        return await eventLoop.run_in_executor(executor or _EXECUTOR, runner)

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


def AsyncOpen(
    file: Union[str, Path],
    mode: str = "r",
    buffering: int = -1,
    encoding: str = None,
    errors: str = None,
    *,
    loop: Optional[AbstractEventLoop] = None,
    executor: Optional[ThreadPoolExecutor] = None,
) -> AiofilesContextManager:
    return aiofiles.open(
        file=file,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        loop=(loop or get_event_loop()),
        executor=(executor or _EXECUTOR),
    )
