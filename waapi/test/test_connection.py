import unittest

from waapi import WaapiClient, connect, CannotConnectToWaapiException


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

    def test_with_statement(self):
        with WaapiClient() as client:
            self.assertTrue(client.is_connected())
            # Implicit disconnect through __exit__
        self.assertFalse(client.is_connected())

    def test_with_statement_cannot_connect(self):
        bad_address = "ws://bad_address/waapi"
        try:
            with WaapiClient(bad_address) as client:
                self.fail("Should not reach this part of the code")
        except CannotConnectToWaapiException as e:
            # Validate the message indicate the incorrect URL
            self.assertIn(bad_address, str(e))
        except Exception:
            self.fail("Should not throw any other error types")
