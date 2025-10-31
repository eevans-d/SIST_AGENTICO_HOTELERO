# Make app.services a proper package and expose selected submodules used by tests
# Expose qr_service for patching in tests like: app.services.qr_service.get_qr_service
from . import qr_service  # noqa: F401
