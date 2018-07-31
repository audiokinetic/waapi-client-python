import time
from copy import copy

from waapi.event import EventHandler
from waapi.async_decoupled_client import WaapiClientAutobahn
from waapi.interface import WampRequest, WampRequestType, CannotConnectToWaapiException, UnsubscribeHandler
from waapi.libs.async_compatibility import asyncio, yield_from
from waapi.libs.ak_autobahn import runner_init


def connect(url=None):
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


class WaapiClient(UnsubscribeHandler):
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
        """:type: Event"""
        self._request_queue = None
        """:type: asyncio.Queue"""

        self._subscriptions = set()
        """:type: set[EventHandler]"""

        if not self._connect():
            raise CannotConnectToWaapiException("Could not connect to " + self._url)

    def _connect(self):
        # Arbitrary queue size of 10, for now
        self._client_thread, self._connected_event, self._request_queue = \
            runner_init(self._url, WaapiClientAutobahn, 10, self._loop)

        # Return upon connection success
        # (Event from threading module here, no need for the asyncio threadsafe wrapper)
        self._connected_event.wait()

        # A failure is indicated by the runner client thread being terminated
        return self._client_thread.is_alive()

    def disconnect(self):
        """
        Disconnect through WampRequestType.STOP
        """
        if not self.is_connected():
            return

        self.__do_request(WampRequestType.STOP)
        self._request_queue = None
        self._subscriptions.clear()  # No need to unsubscribe, subscriptions will be dropped anyways

        # Wait for the runner thread to gracefully exit and the asyncio loop to close
        self._client_thread.join()

        assert(asyncio.get_event_loop().is_closed())
        # Create a new loop for upcoming uses
        asyncio.set_event_loop(asyncio.new_event_loop())

    def is_connected(self):
        return self._connected_event.is_set() and self._client_thread.is_alive()

    def call(self, uri, **kwargs):
        return self.__do_request(WampRequestType.CALL, uri, **kwargs)

    def subscribe(self, uri, callback_or_handler=None, **kwargs):
        """
        :rtype: callable | EventHandler
        :rtype: EventHandler | None
        """
        if callback_or_handler is not None and isinstance(callback_or_handler, EventHandler):
            event_handler = callback_or_handler
        else:
            event_handler = EventHandler(self, callback_or_handler)

        subscription = self.__do_request(WampRequestType.SUBSCRIBE, uri, event_handler.on_event, **kwargs)
        if subscription is not None:
            event_handler.subscription = subscription
            event_handler.unsubscribe_handler = self
            self._subscriptions.add(event_handler)
            return event_handler

    def unsubscribe(self, event_handler):
        if event_handler not in self._subscriptions:
            return

        success = self.__do_request(WampRequestType.UNSUBSCRIBE, subscription=event_handler.subscription)
        if success:
            self._subscriptions.remove(event_handler)
        return success

    def subscriptions(self):
        return copy(self._subscriptions)

    def __do_request(self, request_type, uri=None, callback=None, subscription=None, **kwargs):
        if not self._client_thread.is_alive():
            return

        @asyncio.coroutine
        def _async_request(future):
            request = WampRequest(request_type, uri, kwargs, callback, subscription, future)
            yield from self._request_queue.put(request)
            yield from future  # The client worker is responsible for completing the future

        forwarded_future = asyncio.Future()
        asyncio.run_coroutine_threadsafe(_async_request(forwarded_future), self._loop).result()

        return forwarded_future.result()

    def __del__(self):
        self.disconnect()
