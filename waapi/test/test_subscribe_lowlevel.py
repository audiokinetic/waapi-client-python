import unittest
from threading import Event

from waapi import WaapiClient, EventHandler


class SubscribeLowLevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = WaapiClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()

    def setUp(self):
        self.assertEqual(len(self.client.subscriptions()), 0)

    def tearDown(self):
        # Make sure there is no subscriptions before any test
        for sub in self.client.subscriptions():
            sub.unsubscribe()

    def _create_object(self):
        return self.client.call(
            "ak.wwise.core.object.create",
            parent="\\Actor-Mixer Hierarchy\\Default Work Unit",
            type="Sound",
            name="Some Name"
        )

    def _delete_object(self):
        return self.client.call(
            "ak.wwise.core.object.delete",
            object="\\Actor-Mixer Hierarchy\\Default Work Unit\\Some Name"
        )

    def test_invalid(self):
        handler = self.client.subscribe("ak.wwise.idontexist")
        self.assertIs(handler, None)  # Noexcept
        self.assertEqual(len(self.client.subscriptions()), 0)

    def test_lonely_event_handler(self):
        event_handler = EventHandler()
        self.assertFalse(event_handler.unsubscribe())

        # Should do nothing, noexcept.
        event_handler.on_event()
        event_handler()

    def test_subscribe_no_argument_no_callback(self):
        handler = self.client.subscribe("ak.wwise.core.object.nameChanged")
        self.assertIsNotNone(handler)
        self.assertIsInstance(handler, EventHandler)
        self.assertIsNotNone(handler.subscription)

        self.assertEqual(len(self.client.subscriptions()), 1)
        self.assertTrue(handler.unsubscribe())
        self.assertEqual(len(self.client.subscriptions()), 0)

    def test_subscribe_no_argument_bound_callback(self):
        # Precondition: No object
        self._delete_object()

        handler = self.client.subscribe("ak.wwise.core.object.created")

        class CallbackCounter:
            def __init__(self):
                self._count = 0
                self._event = Event()

            def wait_for_increment(self):
                self._event.wait()
                self._event.clear()

            def increment(self, *args, **kwargs):
                self._count += 1
                self._event.set()

            def count(self):
                return self._count

        callback_counter = CallbackCounter()
        handler.bind(callback_counter.increment)

        self.assertEqual(callback_counter.count(), 0)

        self.assertIsNotNone(self._create_object())

        callback_counter.wait_for_increment()
        self.assertEqual(callback_counter.count(), 1)

        self.assertIsNotNone(self._delete_object())
