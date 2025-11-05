# Test environment tweak: make unittest.mock.Mock behave like MagicMock to support magic methods in tests
# This is loaded automatically by Python when present in sys.path.
import unittest.mock as _mock

# Only adjust if not already MagicMock
if _mock.Mock is not _mock.MagicMock:  # pragma: no cover
    _mock.Mock = _mock.MagicMock
