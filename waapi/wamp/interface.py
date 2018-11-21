from enum import Enum

from autobahn.wamp.request import Subscription
from autobahn.wamp import ApplicationError


class CannotConnectToWaapiException(Exception):
    pass


class WaapiRequestFailed(Exception):
    def __init__(self, application_error):
        """
        :param application_error: Error coming from the Autobahn library
        :type application_error: ApplicationError
        """
        self._error = application_error

    @property
    def uri(self):
        return self._error.error

    @property
    def kwargs(self):
        return self._error.kwargs

    def __str__(self):
        return str(self._error)


class WampRequestType(Enum):
    STOP = 0,
    CALL = 1,
    SUBSCRIBE = 2,
    UNSUBSCRIBE = 3


class WampRequest:
    """
    Structure meant to be used as a payload for requests to a WAMP decoupled client
    """

    def __init__(self, request_type, uri=None, kwargs=None, callback=None, subscription=None, future=None):
        """
        :type request_type: WampRequestType
        :type uri: str | None
        :type kwargs: dict | None
        :type callback: (*Any) -> None | None
        :type subscription: Subscription | None
        :param future: Result future to complete upon processing of the request
        :type future: asyncio.Future
        """
        self.request_type = request_type
        self.uri = uri
        self.kwargs = kwargs or {}
        self.subscription = subscription
        self.callback = callback
        self.future = future
