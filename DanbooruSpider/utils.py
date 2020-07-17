from pathlib import Path
from typing import Optional
from uuid import uuid4

TEMP_FILE_DIR = Path(".") / "data" / "temp"

TEMP_FILE_DIR.mkdir(exist_ok=True)


class TempFile:
    def __init__(
        self, *, folder: Optional[str] = None, ext: str = ".tmp", keep: bool = False
    ) -> None:
        assert ext.startswith(".")
        folderPath = Path(folder or str(TEMP_FILE_DIR))
        self._fullPath = folderPath / f"{uuid4()}{ext}"
        self._fullPath.touch(exist_ok=True)
        self._keep = keep

    def __enter__(self) -> Path:
        return self._fullPath.absolute()

    def __exit__(self, *_) -> None:
        if not self._keep:
            self._fullPath.rmdir()
        return
