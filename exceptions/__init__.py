from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class BuilderLimitExceededException(CustomHTTPException):
    def __init__(self, detail: str = "Builder project limit exceeded"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)

class InvestorConsentRequiredException(CustomHTTPException):
    def __init__(self, detail: str = "Investor consent required for this action"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)

class HoldExpiredException(CustomHTTPException):
    def __init__(self, detail: str = "Hold has expired"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)

class InvalidStatusTransitionException(CustomHTTPException):
    def __init__(self, detail: str = "Invalid status transition"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)

class DoubleBookingException(CustomHTTPException):
    def __init__(self, detail: str = "Property already booked"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)

class InsufficientPermissionsException(CustomHTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)

class ResourceNotFoundException(CustomHTTPException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found")