class DanbooruException(Exception):
    pass


class SpiderException(DanbooruException):
    pass


class NetworkException(SpiderException):
    pass
