from threading import Event

from waapi import EventHandler
from waapi.test.fixture import CleanConnectedClientTestCase


class SubscribeLowLevel(CleanConnectedClientTestCase):

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

    def test_subscribe_no_options_bound_callback(self):
        # Precondition: No object
        self._delete_object()

        handler = self.client.subscribe("ak.wwise.core.object.created")

        class CallbackCounter:
            def __init__(self):
                self._count = 0
                self._event = Event()

            def wait_for_increment(self):
                self._event.wait(CleanConnectedClientTestCase.TIMEOUT_VALUE)
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

    def test_subscribe_with_options(self):
        # Precondition: No object
        self._delete_object()

        event = Event()

        def on_object_created(object):
            self.assertIn("id", object)
            self.assertIn("isPlayable", object)
            self.assertIn("classId", object)

            event.set()

        handler = self.client.subscribe(
            "ak.wwise.core.object.created",
            on_object_created,
            {
                "return": ["id", "isPlayable", "classId"]
            }
        )

        self.assertIsNotNone(self._create_object())
        self.assertTrue(event.wait(self.TIMEOUT_VALUE))
        self.assertIsNotNone(self._delete_object())
        self.assertTrue(handler.unsubscribe())

    def test_subscribe_lambda(self):
        self._delete_object()

        event = Event()

        self.client.subscribe("ak.wwise.core.object.created", lambda object: event.set())
        self._create_object()

        self.assertTrue(event.wait(self.TIMEOUT_VALUE))
        self._delete_object()

    def test_unsubscribed_not_subscribed(self):
        handler = self.client.subscribe("ak.wwise.core.object.created")
        self.assertIsNotNone(handler)
        self.assertTrue(handler.unsubscribe())
        self.assertFalse(handler.unsubscribe())

    def test_cannot_bind_not_callable(self):
        handler = self.client.subscribe("ak.wwise.core.object.created")
        self.assertIsNotNone(handler)
        self.assertIsNone(handler.bind(None))

        class NotCallable:
            pass
        self.assertIsNone(handler.bind(NotCallable()))

    def test_no_callback_valid(self):
        self._delete_object()
        self.client.subscribe("ak.wwise.core.object.created")
        self._create_object()
        # No exception: the callback wrapper ignored the publish
        self._delete_object()
