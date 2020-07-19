from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

Base: DeclarativeMeta = declarative_base()


class Pictures(Base):
    __tablename__ = "pictures"
    pid = Column(Integer, primary_key=True, autoincrement=True)
    md5 = Column(String(40), index=True, unique=True, nullable=False)
    locale_path = Column(String(200), index=True, unique=True, nullable=False)
    rating = Column(String(5), index=True, nullable=False)
    source = Column(String(40), index=True, nullable=False)
    source_id = Column(Integer, index=True, nullable=False)
    source_url = Column(String(300), nullable=False)
    create_time = Column(DateTime, nullable=False, default=datetime.now)


class Tags(Base):
    __tablename__ = "tags"
    tid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), index=True, nullable=False, unique=True)
    create_time = Column(DateTime, nullable=False, default=datetime.now)


class TagRelations(Base):
    __tablename__ = "tag_relations"
    tid = Column(Integer, ForeignKey("tags.tid"), primary_key=True)
    pid = Column(Integer, ForeignKey("pictures.pid"), primary_key=True)
    create_time = Column(DateTime, nullable=False, default=datetime.now)
