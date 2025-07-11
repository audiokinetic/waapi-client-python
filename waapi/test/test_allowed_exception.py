import unittest

from waapi import WaapiClient, WaapiRequestFailed

from waapi.wamp.async_decoupled_client import logger

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

    def test_exception_no_error_logging(self):
        errors = []
        def peek_error(*args, **kwargs):
            errors.append(*args)
            old_error_fct(*args, **kwargs);

        old_error_fct = logger.error
        logger.error = peek_error
        with WaapiClient(allow_exception=True) as client:
            try:
                client.call("ak.wwise.idontexist")
            except WaapiRequestFailed:
                pass
        logger.error = old_error_fct
        self.assertEqual(len(errors), 0)