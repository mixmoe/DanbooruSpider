class DanbooruException(Exception):
    pass


class DatabaseException(DanbooruException):
    pass


class SpiderException(DanbooruException):
    pass


class NetworkException(SpiderException):
    pass


class NotImplementedException(DanbooruException):
    pass
