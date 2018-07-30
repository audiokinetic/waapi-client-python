import logging
import time
from enum import Enum
from pprint import pformat
from threading import Thread, Event

from waapi.libs.async_compatibility import asyncio, yield_from
from waapi.libs.ak_autobahn import AkComponent, runner_init


class CannotConnectToWaapiException(Exception):
    pass


class ClientOwner:
    def __init__(self):
        self._request_queue = None

    def set_request_queue(self, request_queue):
        self._request_queue = request_queue

    def has_client(self):
        return self._request_queue is not None


class WaapiClient(ClientOwner):
    """
    Synchronous Waapi client
    """
    def __init__(self, url=None):
        """
        :param url: URL of the Waapi server,
        :raises: CannotConnectToWaapiException
        """
        super(WaapiClient, self).__init__()

        self._url = url or "ws://127.0.0.1:8080/waapi"
        self._client_thread = None
        """:type: Thread"""
        self._loop = asyncio.get_event_loop()
        self._connected_event = None
        """:type: asyncio.Event"""

        if not self._connect():
            raise CannotConnectToWaapiException("Could not connect to " + self._url)

    def _connect(self):
        # Arbitrary queue size of 10, for now
        self._client_thread, self._connected_event, self._request_queue = \
            runner_init(self._url, WaapiClientAutobahn, self, 10, self._loop)

        # Return upon connection success
        self._connected_event.wait()

        # A failure is indicated by the runner client thread being terminated
        return self._client_thread.is_alive()

    def disconnect(self):
        """
        Disconnect through WampRequestType.STOP
        """
        self.__do_request(WampRequestType.STOP)
        self._request_queue = None

    @classmethod
    def connect(cls, url=None):
        """
        Factory for uniform API across languages.
        Noexcept, returns None if cannot connect.

        :param url: URL of the Waapi server,
        :return: WaapiClient | None
        """
        try:
            return WaapiClient(url)
        except CannotConnectToWaapiException:
            return None

    def call(self, uri, **kwargs):
        return self.__do_request(WampRequestType.CALL, uri, **kwargs)

    def subscribe(self, uri, callback, **kwargs):
        return self.__do_request(WampRequestType.SUBSCRIBE, uri, callback, **kwargs)

    def __do_request(self, request_type, uri=None, callback=None, **kwargs):
        if not self._client_thread.is_alive():
            return

        @asyncio.coroutine
        def _async_request(future):
            request = WampRequest(request_type, uri, kwargs, callback, future)
            yield from self._request_queue.put(request)
            yield from future  # The client worker is responsible for completing the future

        forwarded_future = asyncio.Future()
        asyncio.run_coroutine_threadsafe(_async_request(forwarded_future), self._loop).result()

        return forwarded_future.result()



    def __del__(self):
        self.disconnect()


_logger = logging.getLogger("WaapiClientAutobahn")
_logger.setLevel(logging.DEBUG)
_logger.hasHandlers()


class WampRequestType(Enum):
    STOP = 0,
    CALL = 1,
    SUBSCRIBE = 2


class WampRequest:
    def __init__(self, request_type, uri=None, kwargs=None, callback=None, future=None):
        self.request_type = request_type
        self.uri = uri
        self.kwargs = kwargs
        self.callback = callback or self.default_callback
        self.future = future

    def default_callback(self, result):
        self.future.set_result(result)


class WaapiClientAutobahn(AkComponent):
    """
    Implementation class of a Waapi client using the autobahn library
    """
    def __init__(self, config, request_queue, connected_event):
        """
        :param config: Autobahn configuration
        :type queue_size: int
        """
        super(WaapiClientAutobahn, self).__init__(config)
        self._request_queue = request_queue
        self._connected_event = connected_event

    def _log(self, msg):
        _logger.debug("WaapiClientAutobahn: %s", msg)

    @asyncio.coroutine
    def onJoin(self, details):
        self._log("Joined!")
        self._connected_event.set()

        while True:
            self._log("About to wait on the queue")
            request = yield from self._request_queue.get()
            """:type: WampRequest"""
            self._log("Received something!")

            try:
                if request.request_type is WampRequestType.STOP:
                    self._log("Received STOP, stopping and setting the result")
                    self.disconnect()
                    self._log("Disconnected")
                    request.future.set_result(True)
                    self._log("Set the result event")
                    break
                elif request.request_type is WampRequestType.CALL:
                    self._log("Received CALL, calling " + request.uri)
                    res = yield from(self.call(request.uri, request.kwargs))
                    self._log("Call sent, received response")
                    callback = _WampCallbackHandler(request.callback)
                    callback(**res.kwresults if res else {})
                    request.future.set_result(request.result_value)
                elif request.request_type is WampRequestType.SUBSCRIBE:
                    callback = _WampCallbackHandler(request.callback)
                    res = yield from(self.subscribe(
                        callback,
                        topic=request.uri,
                        options=request.kwargs))
                    request.future.set_result(res is not None)
            except Exception as e:
                self._log(pformat(str(e)))

            self._log("Done treating request!")

    def onDisconnect(self):
        print("The client was disconnected.")
        asyncio.get_event_loop().stop()


class _WampCallbackHandler:
    def __init__(self, callback=None):
        assert callable(callback)
        self._callback = callback

    def __call__(self, *args, **kwargs):
        if self._callback and callable(self._callback):
            self._callback(kwargs)
