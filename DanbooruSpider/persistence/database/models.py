from datetime import datetime

from pydantic import BaseModel


class PicturesCreate(BaseModel):
    md5: str
    locale_path: str
    rating: str
    source: str
    source_id: int
    source_url: str


class PicturesRead(PicturesCreate):
    pid: int
    create_time: datetime


class TagsCreate(BaseModel):
    name: str


class TagsRead(TagsCreate):
    tid: int
    create_time: datetime


class TagsRelationCreate(BaseModel):
    tid: int
    pid: int


class TagsRelationRead(TagsRelationCreate):
    create_time: datetime
