import six
import inspect
from threading import Thread, Event
from pprint import pprint

from waapi.wamp.async_compatibility import asyncio
from waapi.wamp.interface import WampRequestType

import txaio

from autobahn import util
from autobahn.wamp import exception, types, uri
from autobahn.wamp.message import Call, Subscribe
from autobahn.wamp.protocol import CallRequest, is_method_or_function
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.request import Handler, SubscribeRequest


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


def start_decoupled_autobahn_client(url, akcomponent_factory, queue_size, loop, allow_exception):
    """
    Initialize a WAMP client runner in a separate thread with the provided asyncio loop

    :type url: str
    :type akcomponent_factory: (config, AutobahnClientDecoupler) -> AkComponent
    :type queue_size: int
    :type loop: asyncio.AbstractEventLoop
    :type allow_exception: bool
    :rtype: (Thread, AutobahnClientDecoupler)
    """
    runner = ApplicationRunner(url=url, realm=u"realm1")
    decoupler = AutobahnClientDecoupler(queue_size)

    async_client_thread = _WampClientThread(
        runner,
        loop,
        decoupler,
        akcomponent_factory,
        allow_exception
    )
    async_client_thread.start()

    return async_client_thread, decoupler


class _WampClientThread(Thread):
    def __init__(self, runner, loop, decoupler, akcomponent_factory, allow_exception):
        """
        WAMP client thread that runs the asyncio main event loop
        Do NOT terminate this thread to stop the client: use the decoupler to send a STOP request.

        :type runner: ApplicationRunner
        :type loop: asyncio.AbstractEventLoop
        :type decoupler: AutobahnClientDecoupler
        :type akcomponent_factory: (config, AutobahnClientDecoupler, bool) -> AkComponent
        :type allow_exception: False
        """
        super(_WampClientThread, self).__init__()
        self._runner = runner
        self._loop = loop
        self._decoupler = decoupler
        self._akcomponent_factory = akcomponent_factory
        self._allow_exception = allow_exception

    def run(self):
        try:
            asyncio.set_event_loop(self._loop)

            # Start the loop ourselves to skip the sigterm signal handler since
            # it is not supported from a different thread
            coro = self._runner.run(
                lambda config: self._akcomponent_factory(config, self._decoupler, self._allow_exception),
                start_loop=False
            )

            transport, protocol = self._loop.run_until_complete(coro)

            # Info is too verbose, use error by default
            # TODO: Make logging level for autobahn configurable
            txaio.start_logging(level='error')

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
            pprint(e)

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
        if six.PY2 and type(procedure) == str:
            procedure = six.u(procedure)
        assert(isinstance(procedure, six.text_type))
        if not self._transport:
            raise exception.TransportLost()

        request_id = util.id()
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
        if six.PY2 and type(topic) == str:
            topic = six.u(topic)
        assert (topic is None or type(topic) == six.text_type)
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
                    subopts = pat.options or options or types.SubscribeOptions(
                        match=u"wildcard" if pat.uri_type == uri.Pattern.URI_TYPE_WILDCARD else
                              u"exact").message_attr()
                    on_replies.append(self._subscribe(handler, proc, pat.uri(), subopts))
            return txaio.gather(on_replies, consume_exceptions=True)
