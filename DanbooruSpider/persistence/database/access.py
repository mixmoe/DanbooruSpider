from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyException
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session, sessionmaker

from ...config import Config
from ...exceptions import DatabaseException
from ...log import logger
from ...utils import SyncToAsync
from . import models, tables

DatabaseConfig = Config["persistence"]["database"]

Engine = create_engine(
    DatabaseConfig["uri"].as_str(),
    connect_args=DatabaseConfig["uri"].get(dict),
    echo=DatabaseConfig["echo-sql-exec"].get(bool),
)
tables.Base.metadata.create_all(bind=Engine)
SessionFactory: Callable[[], Session] = sessionmaker(bind=Engine, auto_commit=True)


class DatabaseUtils:
    @staticmethod
    def toDict(table: DeclarativeMeta) -> Dict[str, Any]:
        return dict(table.__dict__)

    @classmethod
    def connect(cls) -> "Transaction":
        return cls.Transaction()

    @classmethod
    def process(cls, function: Callable) -> Callable[..., Awaitable]:
        @SyncToAsync
        @wraps(function)
        def wrapper(*args, **kwargs) -> Any:
            logger.trace(f"Database handled for {function.__qualname__}.")
            try:
                with cls.connect() as session:
                    return function(session, *args, **kwargs)
            except SQLAlchemyException as e:
                raise DatabaseException(
                    f"A database error {e} occurred during accessing database."
                )

        return wrapper

    class Transaction:
        def __init__(self, session: Optional[Session] = None) -> None:
            self._session = session or SessionFactory()

        def __enter__(self) -> Session:
            self._session.begin()
            return self._session

        def __exit__(self, *args) -> None:
            if self._session.transaction is not None:
                self._session.transaction.__exit__(*args)
            return


class DatabaseAccess:
    @staticmethod
    @DatabaseUtils.process
    def createPicture(session:Session,data: models.PicturesCreate) -> models.PicturesRead:
        pass
