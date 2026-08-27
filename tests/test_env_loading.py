import os
import unittest

from evren_client import _resolve_api_key


class EnvLoadingTest(unittest.TestCase):
    def test_resolve_api_key_reads_existing_environment_or_example(self):
        old_key = os.environ.get("EVREN_API_KEY")

        try:
<<<<<<< HEAD
            os.environ["EVREN_API_KEY"] = "test_evren_api_key"

            value = _resolve_api_key()
            self.assertIsInstance(value, str)
            self.assertEqual(value, "test_evren_api_key")
=======
            os.environ["EVREN_API_KEY"] = "mock_key_value_long_enough"
            value = _resolve_api_key()
            self.assertEqual(value, "mock_key_value_long_enough")
>>>>>>> 5fd4d78214c1882cc8affbe5a740465ad13f1cb0
        finally:
            if old_key is not None:
                os.environ["EVREN_API_KEY"] = old_key
            else:
                os.environ.pop("EVREN_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
