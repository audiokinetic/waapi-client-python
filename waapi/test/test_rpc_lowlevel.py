from copy import copy

from waapi.test.fixture import ConnectedClientTestCase

class RpcLowLevel(ConnectedClientTestCase):
    def test_invalid(self):
        result = self.client.call("ak.wwise.idontexist")
        self.assertIs(result, None)  # Noexcept

    def test_no_argument(self):
        result = self.client.call("ak.wwise.core.getInfo")
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("apiVersion", result)
        self.assertIn("version", result)

        version = result.get("version")
        self.assertIsNotNone(version)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("build", version)
        self.assertEqual(type(version.get("build")), int)

    def test_with_argument(self):
        myargs = {
            "from": {
                "ofType": [
                    "Project"
                ]
            }
        }
        result = self.client.call("ak.wwise.core.object.get", **myargs)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("return", result)
        result_return = result.get("return")

        self.assertIsNotNone(result_return)
        self.assertTrue(isinstance(result_return, list))
        self.assertEqual(len(result_return), 1)
        self.assertTrue(isinstance(result_return[0], dict))
        result_return = result_return[0]

        # Default is (id, name)
        self.assertIn("id", result_return)
        self.assertIsInstance(result_return.get("id"), str)  # GUID
        self.assertIsInstance(result_return.get("name"), str)

    def test_with_argument_and_return_options(self):
        my_args = {
            "from": {
                "ofType": [
                    "Project"
                ]
            }
        }

        my_options = {
            "return": [
                "name",
                "filePath",
                "workunit:isDirty"
            ]
        }

        def separated_call():
            return self.client.call("ak.wwise.core.object.get", my_args, options=my_options)

        def kwargs_call():
            all_args = copy(my_args)
            all_args["options"] = my_options
            return self.client.call("ak.wwise.core.object.get", **all_args)

        for call in (separated_call, kwargs_call):
            result = call()
            self.assertIsNotNone(result)
            self.assertTrue(isinstance(result, dict))
            self.assertIn("return", result)
            result_return = result.get("return")
            result_return = result_return[0]

            self.assertIn("filePath", result_return)
            self.assertIsInstance(result_return.get("filePath"), str)
            self.assertIn("name", result_return)
            self.assertIsInstance(result_return.get("name"), str)
            self.assertIn("workunit:isDirty", result_return)
            self.assertIsInstance(result_return.get("workunit:isDirty"), bool)
