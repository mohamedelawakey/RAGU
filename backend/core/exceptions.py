from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimitExceededException(HTTPException):
    def __init__(self, detail: str = "Too many requests. Try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


class BadRequestException(HTTPException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class ConflictException(HTTPException):
    def __init__(self, detail: str = "Resource Conflict"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class UserAlreadyExistsException(ConflictException):
    def __init__(self, detail: str = "Email or Username already registered."):
        super().__init__(detail=detail)


class ResourceNotFoundException(HTTPException):
    def __init__(self, resource_name: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} not found.",
        )


class InternalServerException(HTTPException):
    def __init__(
        self, detail: str = "An unexpected internal server error occurred."
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Access Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class PayloadTooLargeException(HTTPException):
    def __init__(self, detail: str = "Payload Too Large"):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=detail,
        )


class UnsupportedMediaTypeException(HTTPException):
    def __init__(self, detail: str = "Unsupported Media Type"):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=detail,
        )
