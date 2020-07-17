from pathlib import Path
from typing import Optional

import confuse

APPLICATION_NAME = "DanbooruSpider"
CONFIG_DIR = Path(".") / "data"
CONFIG_NAME = "config.yml"
DEFAULT_NAME = "config.default.yml"


class ApplicationConfiguration(confuse.Configuration):
    def __init__(self, configPath: Optional[str] = None):
        self._config_path = configPath or str(CONFIG_DIR)
        self._config = str(CONFIG_DIR / CONFIG_NAME)
        self._default = str(CONFIG_DIR / DEFAULT_NAME)
        super().__init__(APPLICATION_NAME)

    def config_dir(self) -> str:
        Path(self._config_path).mkdir(exist_ok=True)
        return str(self._config_path)

    def _add_default_source(self):
        assert Path(self._default).is_file()
        data = confuse.load_yaml(self._default, loader=self.loader)
        self.add(confuse.ConfigSource(data, filename=self._default, default=True))

    def _add_config_source(self):
        if not Path(self._config).is_file():
            Path(self._config).write_bytes(Path(self._default).read_bytes())
        data = confuse.load_yaml(self._config, loader=self.loader)
        self.add(confuse.ConfigSource(data, filename=self._config))


CONFIG = Config = ApplicationConfiguration()
