import unittest

from waapi import WaapiClient, connect, CannotConnectToWaapiException


class LargePayload(unittest.TestCase):
    def test_large_rpc(self):
        with WaapiClient() as client:
            result = client.call("ak.wwise.core.object.get", {
                "from": {
                    "name": ["GameParameter:a" + str(n) for n in range(5000)],
                }
            })
            self.assertTrue(client.is_connected())

if __name__ == "__main__":
    LargePayload().test_large_rpc()