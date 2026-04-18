class ProductNotFoundError(Exception):
    """Raised when a requested product does not exist."""


class ProductInUseError(Exception):
    """Raised when a product cannot be deleted because it is referenced by orders."""


class ServiceUnavailableError(Exception):
    """Raised when an external dependency (e.g. order service) is unreachable."""
