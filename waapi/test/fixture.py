import unittest

from waapi import WaapiClient


class ConnectedClientTestCase(unittest.TestCase):
    TIMEOUT_VALUE = 5  # seconds

    @classmethod
    def setUpClass(cls):
        cls.client = WaapiClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()

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


class CleanConnectedClientTestCase(ConnectedClientTestCase):

    def setUp(self):
        self.assertEqual(len(self.client.subscriptions()), 0)

    def tearDown(self):
        # Make sure there is no subscriptions before any test
        for sub in self.client.subscriptions():
            self.assertTrue(sub.unsubscribe())
