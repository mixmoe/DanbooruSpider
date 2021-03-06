from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Ratings(str, Enum):
    SAFE = "s"
    QUESTIONABLE = "q"
    EXPLICIT = "e"


class DanbooruImage(BaseModel):
    id: int
    source: str
    tags: List[str]
    rating: Ratings
    imageURL: str
    imageMD5: str
    imageExt: str
    metadata: Dict[str, Any]


class ImageDownload(BaseModel):
    source: str
    path: Path
    size: int
    md5: str
    data: DanbooruImage
