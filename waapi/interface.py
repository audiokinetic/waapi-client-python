from enum import Enum


class CannotConnectToWaapiException(Exception):
    pass


class WampRequestType(Enum):
    STOP = 0,
    CALL = 1,
    SUBSCRIBE = 2


class WampRequest:
    def __init__(self, request_type, uri=None, kwargs=None, callback=None, future=None):
        self.request_type = request_type
        self.uri = uri
        self.kwargs = kwargs or {}
        self.callback = callback or self.default_callback
        self.future = future

    def default_callback(self, *args, **kwargs):
        pass
