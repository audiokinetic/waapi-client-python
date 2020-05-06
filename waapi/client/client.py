from sys import platform
from copy import copy

from waapi.client.event import EventHandler
from waapi.client.interface import UnsubscribeHandler
from waapi.wamp.interface import WampRequest, WampRequestType, CannotConnectToWaapiException, WaapiRequestFailed
from waapi.wamp.async_decoupled_client import WampClientAutobahn
from waapi.wamp.async_compatibility import asyncio
from waapi.wamp.ak_autobahn import start_decoupled_autobahn_client


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


def enable_debug_log():
    WampClientAutobahn.enable_debug_log()


class WaapiClient(UnsubscribeHandler):
    """
    Pythonic Wwise Authoring API client with a synchronous looking API.

    Uses asyncio under the hood in a separate thread to which WAMP requests are dispatched.
    Use as a normal API for interacting with Wwise, requires no other special setup.
    Each subscription to a topic is managed by a EventHandler instance for a reference is kept in this client.

    The lifetime of the connection is the lifetime of the instance.
    Creating a global instance will automatically disconnect the client at the end of the program execution.

    Import as:
      from waapi import WaapiClient
    """
    def __init__(self, url=None, allow_exception=False):
        """
        :param url: URL of the Wwise Authoring API WAMP server, defaults to ws://127.0.0.1:8080/waapi
        :type: str
        :param allow_exception: Allow errors on call and subscribe to throw an exception. Default is False.
        :type allow_exception: bool
        :raises: CannotConnectToWaapiException
        """
        super(WaapiClient, self).__init__()

        self._allow_exception = allow_exception
        self._url = url or "ws://127.0.0.1:8080/waapi"
        self._client_thread = None
        """:type: Thread"""

        self._loop = asyncio.get_event_loop()
        if not self._loop.is_running():
            if not self._loop.is_closed():
                self._loop.close()
            if platform == 'win32':
                #  Prefer the ProactorEventLoop event loop on Windows
                self._loop = asyncio.ProactorEventLoop()
            else:
                self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._decoupler = None
        """:type: AutobahnClientDecoupler"""

        self._subscriptions = set()
        """:type: set[EventHandler]"""

        # Connect on instantiation (RAII idiom)
        if not self.__connect():
            raise CannotConnectToWaapiException("Could not connect to " + self._url)

    def __connect(self):
        """
        Connect to the Waapi server.
        Never call this method directly from anywhere else than the constructor to preserve RAII.

        :return: True if connection succeeded, False otherwise.
        :rtype: bool
        """
        # Arbitrary queue size of 32
        # TODO: Test if an unbounded queue might do the job for most cases, add the queue size as a parameter
        self._client_thread, self._decoupler = \
            start_decoupled_autobahn_client(self._url, WampClientAutobahn, 32, self._loop, self._allow_exception)

        # Return upon connection success
        self._decoupler.wait_for_joined()

        # A failure is indicated by the runner client thread being terminated
        return self._client_thread.is_alive()

    def disconnect(self):
        """
        Gracefully disconnect from the Waapi server.

        :return: True if the call caused a successful disconnection, False otherwise.
        :rtype: bool
        """
        if self.is_connected() and self.__do_request(WampRequestType.STOP):
            # Wait for the runner thread to gracefully exit and the asyncio loop to close
            if self._client_thread.is_alive():
                self._client_thread.join()

            self._subscriptions.clear()  # No need to unsubscribe, subscriptions will be dropped anyways

            # Create a new loop for upcoming uses
            if asyncio.get_event_loop().is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())

            return True

        # Only the caller that truly caused the disconnection return True
        return False

    def is_connected(self):
        """
        :return: True if the client is connected, False otherwise.
        :rtype: bool
        """
        return self._decoupler and self._decoupler.has_joined() and self._client_thread.is_alive()

    def call(self, uri, *args, **kwargs):
        """
        Do a Remote Procedure Call (RPC) to the Waapi server.
        Arguments can be specified as named arguments (unless the argument is a reserved keyword), e.g.:
          client.call("my.function", some_argument="Value")

        To avoid reserved keywords restrictions, you may specify a single dictionary, e.g.:
          client.call("my.function", {"some_argument": "Value"})

        Options are accepted using the named argument options, which can also be in the dictionary, e.g.:
          client.call("my.function", some_argument="Value", options={"option1": "Option Value"})
            OR
          client.call("my.function", {"some_argument":"Value", "options":{"option1": "Option Value"}})
            OR
          client.call("my.function", {"some_argument":"Value"}, options={"option1": "Option Value"})

        Note that any named arguments passed take precedence on the values of a dictionary passed as
        a positional argument.

        :param uri: URI of the remote procedure to be called
        :type uri: str
        :param kwargs: Keyword arguments to be passed, options may be passed using the key "options"
        :return: Result from the remote procedure call, None if failed.
        :rtype: dict | None
        :raises: WaapiRequestFailed
        """
        kwargs = self.__merge_args_to_kwargs(args, kwargs)
        return self.__do_request(WampRequestType.CALL, uri, **kwargs)

    def subscribe(self, uri, callback_or_handler=None, *args, **kwargs):
        """
        Subscribe to a topic on the Waapi server.
        Named arguments are options to be passed for the subscription.

        Note that the callback will be called from a different thread.
        Use threading mechanisms to synchronize your code and avoid race conditions.

        Like the call method, you may pass a dictionary to avoid reserved keywords restrictions, e.g.:
          client.subscribe("my.topic", callback, option1="Value", option2="OtherValue")
            OR
          client.subscribe("my.topic", callback, {"option1": "Value", "option2": "OtherValue"})
            OR
          client.subscribe("my.topic", callback, {"option1": "Value"}, option2="OtherValue")

        Note that any named arguments passed take precedence on the values of a dictionary passed as
        a positional argument.

        :param uri: URI of the remote procedure to be called
        :type uri: str
        :param callback_or_handler: A callback that will be called when the server publishes on the provided topic.
                                    The instance can be a function with a matching signature or an instance of a
                                    EventHandler (or subclass).
                                    Note: use a generic signature to support any topic: def fct(*args, **kwargs):
        :type callback_or_handler: callable | EventHandler
        :rtype: EventHandler | None
        :raises: WaapiRequestFailed
        """
        kwargs = self.__merge_args_to_kwargs(args, kwargs)

        if callback_or_handler is not None and isinstance(callback_or_handler, EventHandler):
            event_handler = callback_or_handler
        else:
            event_handler = EventHandler(self, callback_or_handler)

        subscription = self.__do_request(
            WampRequestType.SUBSCRIBE,
            uri,
            event_handler.on_event,
            **kwargs
        )
        if subscription is not None:
            event_handler.subscription = subscription
            event_handler._unsubscribe_handler = self
            self._subscriptions.add(event_handler)
            return event_handler

    def unsubscribe(self, event_handler):
        """
        Unsubscribe from a topic managed by the passed EventHandler instance.

        Alternatively, you may use the unsubscribe method on the EventHandler directly.

        :param event_handler: Event handler that can be found in this client instance's subscriptions
        :type event_handler: EventHandler
        :return: True if successfully unsubscribed, False otherwise.
        :rtype: bool
        """
        if event_handler not in self._subscriptions:
            return False

        success = self.__do_request(WampRequestType.UNSUBSCRIBE, subscription=event_handler.subscription)
        if success:
            self._subscriptions.remove(event_handler)
            event_handler.subscription = None
        return success

    def subscriptions(self):
        """
        :return: A copy of the set of subscriptions belonging to client instance.
        :rtype: set[EventHandler]
        """
        return copy(self._subscriptions)

    @staticmethod
    def __merge_args_to_kwargs(args, kwargs):
        """
        Merged a single dictionary passed as argument to a kwargs dictionary, if it exists.

        :type args: tuple[dict] | tuple[]
        :param kwargs: dict
        :return: Updated kwargs
        :rtype: dict
        """
        if len(args) > 0 and isinstance(args[0], dict):
            kwargs.update(args[0])
        return kwargs

    def __do_request(self, request_type, uri=None, callback=None, subscription=None, **kwargs):
        """
        Create and forward a generic WAMP request to the decoupler

        :type request_type: WampRequestType
        :type uri: str | None
        :type callback: (*Any) -> None | None
        :type subscription: Subscription | None
        :return: Result from WampRequest, None if request failed.
        :rtype: dict | None
        """
        if not self._client_thread.is_alive():
            return

        # Make sure the current thread has the event loop set
        asyncio.set_event_loop(self._loop)

        @asyncio.coroutine
        def _async_request(future):
            """
            :type future: asyncio.Future
            """
            request = WampRequest(request_type, uri, kwargs, callback, subscription, future)
            yield from self._decoupler.put_request(request)
            yield from future  # The client worker is responsible for completing the future

        forwarded_future = asyncio.Future()
        concurrent_future = asyncio.run_coroutine_threadsafe(_async_request(forwarded_future), self._loop)
        self._decoupler.set_caller_future(concurrent_future)
        concurrent_future.result()
        self._decoupler.set_caller_future(None)

        # If the decoupled client worker never set the future, it failed and/or died and we return None
        if forwarded_future.done():
            return forwarded_future.result()

    def __del__(self):
        self.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
