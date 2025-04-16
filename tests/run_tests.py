#!/usr/bin/env python3
"""
Test runner script for Google to Apple Photos Metadata Synchronizer
"""
import unittest
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests():
	"""Run all tests in the tests directory"""
	# Discover and run tests
	test_loader = unittest.TestLoader()
	test_suite = test_loader.discover(os.path.dirname(os.path.abspath(__file__)))
	test_runner = unittest.TextTestRunner(verbosity=2)
	result = test_runner.run(test_suite)
	return result.wasSuccessful()


if __name__ == "__main__":
	success = run_tests()
	sys.exit(0 if success else 1)
