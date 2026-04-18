class OrderServiceError(Exception):
    pass


class OrderNotFoundError(OrderServiceError):
    pass


class ProductNotFoundError(OrderServiceError):
    pass


class ProductServiceUnavailableError(OrderServiceError):
    pass
