import asyncio
from typing import Any, Dict, Optional, Type

from ...config import Config
from ...log import logger
from .impl import DanbooruUnified
from .worker import ListSpiderWorker

ListSpiderConfig = Config["spider"]["lists"]


class ListSpiderManager:
    workers: int = ListSpiderConfig["workers"].as_number()
    _implementations: Dict[str, Type[ListSpiderWorker]] = {}
    _instances: Dict[str, ListSpiderWorker] = {}
    _tasks: Dict[str, asyncio.Task] = {}

    @classmethod
    def register(cls, name: str, implementation: Type[ListSpiderWorker]) -> int:
        assert issubclass(implementation, ListSpiderWorker)
        assert name not in cls._implementations
        cls._implementations[name] = implementation
        logger.debug(f"Registering class {implementation!r} implementation as {name}.")
        return len(cls._implementations)

    @classmethod
    def remove(cls, name: str) -> Type[ListSpiderWorker]:
        assert name in cls._implementations
        logger.debug(f"Removing implementation {name}.")
        return cls._implementations.pop(name)

    @classmethod
    def instance(
        cls, implementation: str, name: str, config: Optional[Dict[str, Any]] = None
    ) -> ListSpiderWorker:
        config = config or {}
        assert implementation in cls._implementations
        assert name not in cls._instances
        worker: Type[ListSpiderWorker] = cls._implementations[implementation]
        workerInstance: ListSpiderWorker = worker(**config)
        cls._instances[name] = workerInstance
        logger.info(
            f"Instance of {implementation} has been created as {name} with config {config!r}."
        )
        return workerInstance

    @classmethod
    async def run(cls, name: str) -> asyncio.Queue:
        async def queuePutter(worker: ListSpiderWorker, queue: asyncio.Queue) -> None:
            async for result in worker.run():
                await queue.put(result)

        while (
            len([*filter(lambda t: not t.done(), cls._tasks.values())]) >= cls.workers
        ):
            await asyncio.sleep(1)

        assert name in cls._instances
        assert name not in cls._tasks
        worker: ListSpiderWorker = cls._instances[name]
        queue: asyncio.Queue = asyncio.Queue(ListSpiderConfig["queue-size"].as_number())
        workTask = queuePutter(worker, queue)
        cls._tasks[name] = asyncio.create_task(workTask, name=name)
        logger.info(f"Task of instance {name} created.")
        return queue

    @classmethod
    def cancel(cls, name: str) -> bool:
        assert name in cls._tasks
        task: asyncio.Task = cls._tasks[name]
        logger.info(f"Task of instance {name} canceled.")
        return task.cancel()


ListSpiderManager.register("danbooru-unified", DanbooruUnified)
