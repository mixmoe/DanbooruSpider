from DanbooruSpider.log import LOGGER_FILE_DIR


class DanbooruException(Exception):
    pass


class SpiderException(DanbooruException):
    pass


class NetworkException(SpiderException):
    pass
