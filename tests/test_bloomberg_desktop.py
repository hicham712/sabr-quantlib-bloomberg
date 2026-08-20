import sys
from types import SimpleNamespace


# The live adapter is integration-tested on a Bloomberg Windows machine. This
# test only verifies that importing the module remains safe without blpapi.
def test_import_without_bloomberg_package():
    import src.bloomberg_desktop as module
    assert hasattr(module, "BloombergDesktopClient")
    assert hasattr(module, "BloombergError")
