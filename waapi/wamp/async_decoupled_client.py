import logging
from pprint import pformat
from threading import Thread

from autobahn.wamp import ApplicationError

from waapi.wamp.interface import WampRequestType, WampRequest, WaapiRequestFailed
from waapi.wamp.ak_autobahn import AkComponent
from waapi.wamp.async_compatibility import asyncio


class WampClientAutobahn(AkComponent):
    """
    Implementation class of a Waapi client using the autobahn library
    """
    logger = logging.getLogger("WampClientAutobahn")

    def __init__(self, config, decoupler, allow_exception):
        """
        :param config: Autobahn configuration
        :type decoupler: AutobahnClientDecoupler
        :param allow_exception: True to allow exception, False to ignore them.
                                In any case they are logged to stderr.
        """
        super(WampClientAutobahn, self).__init__(config)
        self._decoupler = decoupler
        self._allow_exception = allow_exception

    @classmethod
    def enable_debug_log(cls):
        cls.logger.setLevel(logging.DEBUG)

    @classmethod
    def _log(cls, msg):
        cls.logger.debug("WampClientAutobahn: %s", msg)

    @asyncio.coroutine
    def stop_handler(self, request):
        """
        :param request: WampRequest
        """
        self._log("Received STOP, stopping and setting the result")
        self.disconnect()
        self._log("Disconnected")
        request.future.set_result(True)

    @asyncio.coroutine
    def call_handler(self, request):
        """
        :param request: WampRequest
        """
        self._log("Received CALL, calling " + request.uri)
        res = yield from self.call(request.uri, **request.kwargs)
        self._log("Received response for call")
        result = res.kwresults if res else {}
        if request.callback:
            self._log("Callback specified, calling it")
            callback = _WampCallbackHandler(request.callback)
            callback(result)
        request.future.set_result(result)

    @asyncio.coroutine
    def subscribe_handler(self, request):
        """
        :param request: WampRequest
        """
        self._log("Received SUBSCRIBE, subscribing to " + request.uri)
        callback = _WampCallbackHandler(request.callback)
        subscription = yield from (self.subscribe(
            callback,
            topic=request.uri,
            options=request.kwargs)
        )
        request.future.set_result(subscription)

    @asyncio.coroutine
    def unsubscribe_handler(self, request):
        """
        :param request: WampRequest
        """
        self._log("Received UNSUBSCRIBE, unsubscribing from " + str(request.subscription))
        try:
            # Successful unsubscribe returns nothing
            yield from request.subscription.unsubscribe()
            request.future.set_result(True)
        except ApplicationError:
            request.future.set_result(False)
        except Exception as e:
            self._log(str(e))
            request.future.set_result(False)

    @asyncio.coroutine
    def onJoin(self, details):
        self._log("Joined!")
        self._decoupler.set_joined()

        try:
            while True:
                self._log("About to wait on the queue")
                request = yield from self._decoupler.get_request()
                """:type: WampRequest"""
                self._log("Received something!")

                try:
                    handler = {
                        WampRequestType.STOP: self.stop_handler,
                        WampRequestType.CALL: self.call_handler,
                        WampRequestType.SUBSCRIBE: self.subscribe_handler,
                        WampRequestType.UNSUBSCRIBE: self.unsubscribe_handler
                    }.get(request.request_type)

                    if handler:
                        yield from handler(request)
                    else:
                        self._log("Undefined WampRequestType")
                except ApplicationError as e:
                    self.logger.error("WampClientAutobahn (ERROR): " + pformat(str(e)))

                    if self._allow_exception:
                        request.future.set_exception(WaapiRequestFailed(e))
                    else:
                        request.future.set_result(None)

                self._log("Done treating request")

                if request.request_type == WampRequestType.STOP:
                    break

        except RuntimeError:
            # The loop has been shut down by a disconnect
            pass

    def onDisconnect(self):
        self._log("The client was disconnected.")

        # Stop the asyncio loop, ultimately stopping the runner thread
        asyncio.get_event_loop().stop()


class _WampCallbackHandler:
    """
    Wrapper for a callback that unwraps a WAMP response
    """
    def __init__(self, callback=None):
        assert callable(callback)
        self._callback = callback

    def __call__(self, *args, **kwargs):
        if self._callback and callable(self._callback):
            # Use a proper thread so that we can nest calls without blocking in the event loop
            # TODO: Consider using a ThreadPool rather than instantiating a thread each time
            Thread(target=lambda: self._callback(**kwargs)).start()
