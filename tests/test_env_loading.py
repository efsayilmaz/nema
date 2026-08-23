import os
import unittest

from gorev1.agent import _resolve_api_key


class EnvLoadingTest(unittest.TestCase):
    def test_resolve_api_key_reads_existing_environment_or_example(self):
        old_key = os.environ.get("GEMINI_API_KEY")
        old_google_key = os.environ.get("GOOGLE_API_KEY")

        try:
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)

            value = _resolve_api_key()
            self.assertIsInstance(value, str)
            self.assertGreater(len(value), 10)
        finally:
            if old_key is not None:
                os.environ["GEMINI_API_KEY"] = old_key
            if old_google_key is not None:
                os.environ["GOOGLE_API_KEY"] = old_google_key


if __name__ == "__main__":
    unittest.main()
