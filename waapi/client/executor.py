from threading import Thread
from queue import Queue

from waapi.client.interface import CallbackExecutor
from waapi.wamp.async_compatibility import asyncio


class PerCallbackThreadExecutor(CallbackExecutor):
    def execute(self, callback, kwargs):
        Thread(target=lambda: callback(**kwargs)).start()

class SequentialThreadExecutor(CallbackExecutor):
    class ThreadQueuePoison:
        pass
    poison = ThreadQueuePoison()
    publish_queue = Queue()

    @classmethod
    def sequential_executor(cls):
        while True:
            publish = cls.publish_queue.get()
            if publish is cls.poison:
                break
            publish()

    def start(self):
        Thread(target=SequentialThreadExecutor.sequential_executor).start()

    def stop(self):
        SequentialThreadExecutor.publish_queue.put(SequentialThreadExecutor.poison)

    def execute(self, callback, kwargs):
        self.publish_queue.put(lambda: callback(**kwargs))

class AsyncioLoopExecutor(CallbackExecutor):
    def execute(self, callback, kwargs):
        if asyncio.get_event_loop().is_running():
            handler_future = asyncio.Future()
            async def _async_request(cb, future):
                """
                :type future: asyncio.Future
                """
                cb(**kwargs)
                future.set_result(True)

            # Run as a coroutine on the asyncio loop
            concurrent_future = asyncio.run_coroutine_threadsafe(
                _async_request(callback, handler_future),
                asyncio.get_event_loop()
            )
