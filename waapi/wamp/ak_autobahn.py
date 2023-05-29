import inspect
import random
import txaio
from sys import stderr
from threading import Thread, Event
from pprint import pformat

from waapi.wamp.async_compatibility import asyncio
from waapi.wamp.interface import WampRequestType

from autobahn.asyncio.websocket import WampWebSocketClientFactory
from autobahn.asyncio.wamp import ApplicationSession

from autobahn.websocket.util import parse_url as parse_ws_url

from autobahn.wamp import exception, uri
from autobahn.wamp.message import Call, Subscribe
from autobahn.wamp.protocol import CallRequest, is_method_or_function
from autobahn.wamp.request import Handler, SubscribeRequest
from autobahn.wamp.types import SubscribeOptions


class AutobahnClientDecoupler:
    """
    Decoupler for an autobahn client that indicates when the connection has been made and
    manages a queue for requests (WampRequest)
    """
    def __init__(self, queue_size):
        self._request_queue = asyncio.Queue(queue_size)
        self._future = None
        self._stopping = False
        """:type: concurrent.futures.Future"""

        # Do not use the asyncio loop, otherwise failure to connect will stop
        # the loop and the caller will never be notified!
        self._joined_event = Event()

    def wait_for_joined(self):
        self._joined_event.wait()

    def set_joined(self):
        self._joined_event.set()

    def has_joined(self):
        return self._joined_event.is_set()

    def put_request(self, request):
        """
        Put a WampRequest in the decoupled client processing queue as a coroutine
        :type request: WampRequest
        :return: Generator that completes when the queue can accept the request
        """
        # On first reception of a STOP request, immediately complete other requests with None
        if request.request_type == WampRequestType.STOP and not self._stopping:
            self._stopping = True
        elif self._stopping:
            async def stop_now():
                return request.future.set_result(None)
            return stop_now()

        return self._request_queue.put(request)

    def get_request(self):
        """
        Get a WampRequest from the decoupled client processing queue as a coroutine
        :return: Generator to a WampRequest when one is available
        """
        return self._request_queue.get()

    def set_caller_future(self, concurrent_future):
        self._future = concurrent_future

    def unblock_caller(self):
        if self._future:
            self._future.set_result(None)


def start_decoupled_autobahn_client(url, loop, akcomponent_factory, callback_executor, allow_exception, queue_size):
    """
    Initialize a WAMP client runner in a separate thread with the provided asyncio loop

    :type url: str
    :type loop: asyncio.AbstractEventLoop
    :type akcomponent_factory: (AutobahnClientDecoupler, CallbackExecutor, bool) -> AkComponent
    :type callback_executor: CallbackExecutor
    :type allow_exception: bool
    :type queue_size: int
    :rtype: (Thread, AutobahnClientDecoupler)
    """
    decoupler = AutobahnClientDecoupler(queue_size)

    async_client_thread = _WampClientThread(
        url,
        loop,
        akcomponent_factory,
        callback_executor,
        allow_exception,
        decoupler
    )
    async_client_thread.start()

    return async_client_thread, decoupler


class _WampClientThread(Thread):
    def __init__(self, url, loop, akcomponent_factory, callback_executor, allow_exception, decoupler):
        """
        WAMP client thread that runs the asyncio main event loop
        Do NOT terminate this thread to stop the client: use the decoupler to send a STOP request.

        :type url: str
        :type loop: asyncio.AbstractEventLoop
        :type akcomponent_factory: (AutobahnClientDecoupler, CallbackExecutor, bool) -> AkComponent
        :type callback_executor: CallbackExecutor
        :type allow_exception: bool
        :type decoupler: AutobahnClientDecoupler
        """
        super(_WampClientThread, self).__init__()
        self._url = url
        self._loop = loop
        self._decoupler = decoupler
        self._akcomponent_factory = akcomponent_factory
        self._callback_executor = callback_executor
        self._allow_exception = allow_exception

    def run(self):
        try:
            asyncio.set_event_loop(self._loop)

            txaio.use_asyncio()
            txaio.config.loop = self._loop

            # create a WAMP-over-WebSocket transport client factory
            transport_factory = WampWebSocketClientFactory(
                lambda: self._akcomponent_factory(self._decoupler, self._callback_executor, self._allow_exception),
                url=self._url
            )

            # Basic settings with most features disabled
            transport_factory.setProtocolOptions(
                failByDrop=False,
                openHandshakeTimeout=5.,
                closeHandshakeTimeout=1.
            )

            isSecure, host, port, _, _, _ = parse_ws_url(self._url)
            transport, protocol = self._loop.run_until_complete(
                self._loop.create_connection(
                    transport_factory,
                    host,
                    port,
                    ssl=isSecure
                )
            )

            try:
                self._loop.run_forever()
            except KeyboardInterrupt:
                # wait until we send Goodbye if user hit ctrl-c
                # (done outside this except so SIGTERM gets the same handling)
                pass

            # give Goodbye message a chance to go through, if we still
            # have an active session
            if protocol._session:
                self._loop.run_until_complete(protocol._session.leave())

            self._loop.close()
        except Exception as e:
            errorStr = pformat(e)
            stderr.write(errorStr + "\n")

            # Wake the caller, this thread will terminate right after so the
            # error can be detected by checking if the thread is alive
            self._decoupler.set_joined()

        self._decoupler.unblock_caller()


class AkCall(Call):
    """
    Special implementation with support for custom options
    """
    def __init__(self, request, procedure, args=None, kwargs=None):
        super(AkCall, self).__init__(request, procedure, args, kwargs)
        self.options = kwargs.pop(u"options", {})

    def marshal(self):
        """
        Reimplemented to return a fully formed message with custom options
        """
        res = [Call.MESSAGE_TYPE, self.request, self.options, self.procedure, self.args or []]
        if self.kwargs:
            res.append(self.kwargs)
        return res


class AkSubscribe(Subscribe):
    """
    Special implementation with support for custom options
    """
    def __init__(self, request, topic, options=None):
        super(AkSubscribe, self).__init__(request, topic)
        self.options = options or {}

    def marshal(self):
        """
        Reimplemented to return a fully formed message with custom options
        """
        return [Subscribe.MESSAGE_TYPE, self.request, self.options, self.topic]


class AkComponent(ApplicationSession):
    def call(self, procedure, *args, **kwargs):
        """
        Reimplemented to support calls with custom options
        """
        if not self._transport:
            raise exception.TransportLost()

        request_id = random.randint(0, 9007199254740992)
        on_reply = txaio.create_future()
        self._call_reqs[request_id] = CallRequest(request_id, procedure, on_reply, {})

        try:
            self._transport.send(AkCall(request_id, procedure, args, kwargs))
        except Exception as e:
            if request_id in self._call_reqs:
                del self._call_reqs[request_id]
            raise e
        return on_reply

    def _subscribe(self, obj, fn, topic, options):
        request_id = self._request_id_gen.next()
        on_reply = txaio.create_future()
        handler_obj = Handler(fn, obj, None)
        self._subscribe_reqs[request_id] = SubscribeRequest(request_id, topic, on_reply, handler_obj)
        self._transport.send(AkSubscribe(request_id, topic, options))
        return on_reply

    def subscribe(self, handler, topic=None, options=None):
        """
        Implements :func:`autobahn.wamp.interfaces.ISubscriber.subscribe`
        """
        assert (topic is None or type(topic) == str)
        assert((callable(handler) and topic is not None) or hasattr(handler, '__class__'))
        assert (options is None or isinstance(options, dict))

        if not self._transport:
            raise exception.TransportLost()

        if callable(handler):
            # subscribe a single handler
            return self._subscribe(None, handler, topic, options)
        else:
            # subscribe all methods on an object decorated with "wamp.subscribe"
            on_replies = []
            for k in inspect.getmembers(handler.__class__, is_method_or_function):
                proc = k[1]
                wampuris = filter(lambda x: x.is_handler(), proc.__dict__.get("_wampuris")) or ()
                for pat in wampuris:
                    subopts = pat.options or options or SubscribeOptions(
                        match=u"wildcard" if pat.uri_type == uri.Pattern.URI_TYPE_WILDCARD else
                              u"exact").message_attr()
                    on_replies.append(self._subscribe(handler, proc, pat.uri(), subopts))
            return txaio.gather(on_replies, consume_exceptions=True)
