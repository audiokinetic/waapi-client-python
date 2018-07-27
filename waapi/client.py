import logging
import time
from enum import Enum
from pprint import pformat
from threading import Thread

from waapi.libs.async_compatibility import asyncio, yield_from
from waapi.libs.ak_autobahn import AkComponent, runner_init


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
        """
        super(WaapiClient, self).__init__()

        self._url = url or "ws://127.0.0.1:8080/waapi"
        self._client_thread = None
        """:type: Thread"""
        self._loop = asyncio.get_event_loop()

        self._connect()

    def _connect(self):
        # Arbitrary queue size of 10, for now
        self._client_thread, self._request_queue = runner_init(self._url, WaapiClientAutobahn, self, 10, self._loop)

    def disconnect(self):
        """
        Disconnect through WampRequestType.STOP
        """
        self.__do_request(WampRequestType.STOP)
        self._request_queue = None

    @classmethod
    def connect(cls, url=None):
        """
        Factory for uniform API across languages
        :param url: URL of the Waapi server,
        :return: WaapiClient
        """
        return WaapiClient(url)

    def __do_request(self, request_type, uri=None, callback=None, **kwargs):
        if not self._client_thread.is_alive():
            return

        request = WampRequest(self._loop, request_type, uri, kwargs, callback)
        asyncio.run_coroutine_threadsafe(self._request_queue.put(request), self._loop).result()

        print("WaapiClient: waiting on result_event")
        asyncio.run_coroutine_threadsafe(request.result_event.wait(), self._loop).result()
        print("WaapiClient: result_event was set!")

        return request.result_value

    def call(self, uri, **kwargs):
        self.__do_request(WampRequestType.CALL, uri, kwargs)

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
    def __init__(self, loop, request_type, uri=None, kwargs=None, callback=None):
        self.request_type = request_type
        self.uri = uri
        self.kwargs = kwargs
        self.result_event = asyncio.Event(loop=loop)
        self.result_value = None
        self.callback = callback

    def default_callback(self, result):
        self.result_value = result


class WaapiClientAutobahn(AkComponent):
    """
    Implementation class of a Waapi client using the autobahn library
    """
    def __init__(self, config, request_queue):
        """
        :param config: Autobahn configuration
        :type queue_size: int
        """
        super(WaapiClientAutobahn, self).__init__(config)
        self._request_queue = request_queue

    def _log(self, msg):
        _logger.debug("WaapiClientAutobahn: %s", msg)

    @asyncio.coroutine
    def onJoin(self, details):

        self._log("Joined!")
        while True:
            request = yield from self._request_queue.get()
            """:type: WampRequest"""
            self._log("Received something!")

            try:
                if request.request_type is WampRequestType.STOP:
                    self._log("Received STOP, stopping and setting the result")
                    self.disconnect()
                    self._log("Disconnected")
                    request.result_event.set()
                    self._log("Set the result event")
                    break
                elif request.request_type is WampRequestType.CALL:
                    res = yield from(self.call(request.uri, request.kwargs))
                    callback = _WampCallbackHandler(request.callback)
                    callback(**res.kwresults if res else {})
                    request.result_event.set()
                elif request.request_type is WampRequestType.SUBSCRIBE:
                    callback = _WampCallbackHandler(request.callback)
                    yield from(self.subscribe(
                        callback,
                        topic=request.uri,
                        options=request.kwargs))
                    request.result_event.set()
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
