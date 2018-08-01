from threading import Event

from waapi.test.fixture import CleanConnectedClientTestCase


class Integration(CleanConnectedClientTestCase):
    def test_rpc_in_subscribe_callback(self):
        self._delete_object()

        event = Event()
        handler = None

        def my_callback(object):
            # Do a RPC call to delete the object
            self.assertIn("id", object)
            res = self.client.call("ak.wwise.core.object.delete", object=object.get("id"))
            self.assertIsNotNone(res)
            self.assertIsInstance(res, dict)
            self.assertEqual(len(res), 0)

            self.assertIsNotNone(handler)
            self.assertTrue(handler.unsubscribe())

            event.set()

        handler = self.client.subscribe(
            "ak.wwise.core.object.created",
            my_callback,
            **{"return": ["id"]}
        )

        self.assertIsNotNone(handler)
        self._create_object()
        self.assertTrue(event.wait(self.TIMEOUT_VALUE))
