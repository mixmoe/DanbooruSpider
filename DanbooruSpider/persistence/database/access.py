from functools import wraps
from threading import Lock as threadLock
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import Table
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session, sessionmaker

from ...config import Config
from ...exceptions import DatabaseException
from ...log import logger
from ...utils import SyncToAsync
from . import models, tables

DatabaseConfig = Config["persistence"]["database"]
ThreadLock = threadLock()


def processDatabaseAccess(func: Callable) -> Callable[..., Awaitable]:
    @SyncToAsync
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger.trace(f"Accessing database via function {func.__qualname__!r}.")
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            raise DatabaseException(
                f"A database error {e} occurred during executing function {func.__qualname__!r}"
            )

    return wrapper


class DatabaseNotFoundException(DatabaseException):
    pass


class DatabaseConflictException(DatabaseException):
    pass


class DatabaseAccessRoot:
    @staticmethod
    def toDict(table: DeclarativeMeta) -> Dict[str, Any]:
        return dict(table.__dict__)

    class Transaction:
        def __init__(self, session: Session) -> None:
            self._session = session

        def __enter__(self) -> Session:
            self._session.begin()
            ThreadLock.acquire()
            return self._session

        def __exit__(self, *args) -> None:
            ThreadLock.release()
            if self._session.transaction is not None:
                self._session.transaction.__exit__(*args)
            return

    def __init__(self, table: DeclarativeMeta, name: Optional[str] = None) -> None:
        self.table = table
        self._engine = create_engine(
            DatabaseConfig["uri"].as_str(),
            connect_args=DatabaseConfig["connect-args"].get(dict),
            echo=DatabaseConfig["echo-sql-exec"].get(bool),
        )
        self._sessionfactory: Callable[[], Session] = sessionmaker(
            bind=self._engine, autocommit=True
        )
        tableMetadata: Table = self.table.__table__
        tableMetadata.name = name or self.table.__tablename__
        tableMetadata.create(bind=self._engine, checkfirst=True)

    def connect(self) -> "Transaction":
        return self.Transaction(self._sessionfactory())


class PicturesAccess(DatabaseAccessRoot):
    def __init__(self) -> None:
        super().__init__(table=tables.Pictures)
        self.table: tables.Pictures

    @processDatabaseAccess
    def create(self, data: models.PicturesCreate) -> models.PicturesRead:
        tableData = self.table(**data.dict())
        with self.connect() as session:
            if session.query(self.table).filter(self.table.md5 == data.md5).first():
                raise DatabaseConflictException
            session.add(tableData)
            session.flush()
            result = models.PicturesRead(**self.toDict(tableData))
        return result

    @processDatabaseAccess
    def read(
        self, *, pid: Optional[int] = None, md5: Optional[str] = None
    ) -> models.PicturesRead:
        assert (pid or md5) is not None
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(True if md5 is None else (self.table.md5 == md5))
                .filter(True if pid is None else (self.table.pid == pid))
                .first()
            )
            if not queryResult:
                raise DatabaseNotFoundException
            result = models.PicturesRead(**self.toDict(queryResult))
        return result

    @processDatabaseAccess
    def delete(self, *, pid: Optional[int] = None, md5: Optional[str] = None) -> None:
        assert (pid or md5) is not None
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(True if md5 is None else (self.table.md5 == md5))
                .filter(True if pid is None else (self.table.pid == pid))
                .first()
            )
            if not queryResult:
                raise DatabaseNotFoundException
            session.delete(queryResult)
        return


class TagsAccess(DatabaseAccessRoot):
    def __init__(self) -> None:
        super().__init__(table=tables.Tags)
        self.table: tables.Tags

    @processDatabaseAccess
    def create(self, tags: List[models.TagsCreate]) -> List[models.TagsRead]:
        with self.connect() as session:
            newrows = [
                self.table(**i.dict())
                for i in tags
                if not session.query(self.table)
                .filter(self.table.name == i.name)
                .first()
            ]
            session.add_all(newrows)
            session.flush()
            results = [models.TagsRead(**i) for i in map(self.toDict, newrows)]
        return results

    @processDatabaseAccess
    def read(
        self, *, tid: Optional[int] = None, name: Optional[str] = None
    ) -> models.TagsRead:
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(True if tid is None else (self.table.tid == tid))
                .filter(True if name is None else (self.table.name == name))
                .first()
            )
            if not queryResult:
                raise DatabaseNotFoundException
            result = models.TagsRead(**self.toDict(queryResult))
        return result

    @processDatabaseAccess
    def delete(self, *, tid: Optional[int] = None, name: Optional[str] = None):
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(True if tid is None else (self.table.tid == tid))
                .filter(True if name is None else (self.table.name == name))
                .first()
            )
            if not queryResult:
                raise DatabaseNotFoundException
            session.delete(queryResult)
        return


class TagsRelationAccess(DatabaseAccessRoot):
    def __init__(self) -> None:
        super().__init__(table=tables.TagRelations)
        self.table: tables.TagRelations

    @processDatabaseAccess
    def create(
        self, relations: List[models.TagsRelationCreate]
    ) -> List[models.TagsRelationRead]:
        with self.connect() as session:
            newrelations = [
                self.table(**i.dict())
                for i in relations
                if not session.query(self.table)
                .filter(self.table.tid == i.tid)
                .filter(self.table.pid == i.pid)
                .first()
            ]
            session.add_all(newrelations)
            session.flush()
            result = [
                models.TagsRelationRead(**i) for i in map(self.toDict, newrelations)
            ]
        return result

    @processDatabaseAccess
    def read(
        self, *, tid: Optional[int] = None, pid: Optional[int] = None
    ) -> List[models.TagsRelationRead]:
        assert (pid or tid) is not None
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(True if pid is None else (self.table.pid == pid))
                .filter(True if tid is None else (self.table.tid == tid))
                .all()
            )
            result = [
                models.TagsRelationRead(**i) for i in map(self.toDict, queryResult)
            ]
        return result

    @processDatabaseAccess
    def delete(self, tid: int, pid: int) -> None:
        with self.connect() as session:
            queryResult = (
                session.query(self.table)
                .filter(self.table.tid == tid)
                .filter(self.table.pid == pid)
                .first()
            )
            if not queryResult:
                raise DatabaseNotFoundException
            session.delete(queryResult)
        return
