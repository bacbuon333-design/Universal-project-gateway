"""Validation that becomes green only after the isolated demo edit."""

import unittest

from src.greeting import greeting


class GreetingTests(unittest.TestCase):
    def test_gateway_greeting(self) -> None:
        self.assertEqual(greeting(), "Hello from UPG")


if __name__ == "__main__":
    unittest.main()
