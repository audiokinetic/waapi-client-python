from threading import Event

from waapi.test.fixture import CleanConnectedClientTestCase
from waapi import WaapiClient, \
    PerCallbackThreadExecutor, \
    SequentialThreadExecutor, \
    AsyncioLoopExecutor


def _executor_test(self):
    expected = [str(i) for i in range(5)]
    result = []

    self._delete_objects_if_exists(expected)
    event = Event()

    def created(*args, **kwargs):
        nonlocal result
        result.append(kwargs.get("newName"))
        if len(result) == len(expected):
            event.set()

    self.client.subscribe("ak.wwise.core.object.nameChanged", created)
    for name in expected:
        self._create_object(name)

    self.assertTrue(event.wait(self.TIMEOUT_VALUE))
    self.assertListEqual(expected, result)

    for name in expected:
        self._delete_object(name)

class PerCallbackThreadClient(CleanConnectedClientTestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = WaapiClient(callback_executor=PerCallbackThreadExecutor)

    def test_subscribe(self):
        _executor_test(self)

class SequentialThreadClient(CleanConnectedClientTestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = WaapiClient(callback_executor=SequentialThreadExecutor)

    def test_subscribe(self):
        _executor_test(self)

class AsyncioLoopClient(CleanConnectedClientTestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = WaapiClient(callback_executor=AsyncioLoopExecutor)

    def test_subscribe(self):
        _executor_test(self)
