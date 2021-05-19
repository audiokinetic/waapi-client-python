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

    def _create_object(self, name=None):
        return self.client.call(
            "ak.wwise.core.object.create",
            parent="\\Actor-Mixer Hierarchy\\Default Work Unit",
            type="Sound",
            name=name or "Some Name"
        )

    def _delete_object(self, name=None):
        return self.client.call(
            "ak.wwise.core.object.delete",
            object=f"\\Actor-Mixer Hierarchy\\Default Work Unit\\{name or 'Some Name'}"
        )

    def _delete_objects_if_exists(self, names=None):
        names = names or ["Some Name"]
        result = self.client.call(
            "ak.wwise.core.object.get", {
                "from": {
                    "path": [
                        "\\Actor-Mixer Hierarchy\\Default Work Unit"
                    ]
                },
                "transform": [
                    {"select": ["children"]}
                ]
            }
        )
        objects = result.get("return", {})
        for obj in objects:
            object_name = obj.get("name")
            if obj.get("name") in names:
                self._delete_object(object_name)

class CleanConnectedClientTestCase(ConnectedClientTestCase):

    def setUp(self):
        self.assertEqual(len(self.client.subscriptions()), 0)

    def tearDown(self):
        # Make sure there is no subscriptions before any test
        for sub in self.client.subscriptions():
            self.assertTrue(sub.unsubscribe())
