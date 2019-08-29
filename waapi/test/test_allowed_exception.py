import unittest

from waapi import WaapiClient, WaapiRequestFailed


class AllowedException(unittest.TestCase):
    def test_exception_on_unknown_uri(self):
        with WaapiClient(allow_exception=True) as client:
            try:
                client.call("i.dont.exist", someArg=True)
            except WaapiRequestFailed as e:
                self.assertEqual(e.kwargs.get("message"), "The procedure URI is unknown.")
                return

            self.fail("Should have thrown an exception")

    def test_exception_on_invalid_argument(self):
        with WaapiClient(allow_exception=True) as client:
            try:
                client.call("ak.wwise.core.getInfo", someArg=True)
            except WaapiRequestFailed as e:
                self.assertEqual(e.kwargs.get("details", {}).get("typeUri", ""), "ak.wwise.schema_validation_failed")
                return

            self.fail("Should have thrown an exception")
