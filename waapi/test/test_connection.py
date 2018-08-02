import unittest

from waapi import WaapiClient, connect


class Connection(unittest.TestCase):
    def test_connect_constructor(self):
        client = WaapiClient()
        self.assertIsNotNone(client)
        self.assertTrue(client.is_connected())
        # Implicit disconnect through __del__

    def test_connect_function(self):
        client = connect()
        self.assertIsNotNone(client)
        self.assertTrue(client.is_connected())
        # Implicit disconnect through __del__

    def test_disconnect(self):
        client = WaapiClient()
        self.assertTrue(client.is_connected())
        client.disconnect()
        self.assertFalse(client.is_connected())

    def test_cannot_connect(self):
        client = connect("ws://bad_address/waapi")
        self.assertIsNone(client)
