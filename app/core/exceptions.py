class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InsufficientStockError(ConflictError):
    code = "insufficient_stock"


class ValidationFailed(DomainError):
    status_code = 422
    code = "validation_error"


class BusinessRuleError(DomainError):
    status_code = 422
    code = "business_rule_violation"
