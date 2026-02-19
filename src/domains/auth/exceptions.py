from core.exception.exceptions import BaseCustomException
from core.exception.errors import ErrorCode


class InvalidCredentialsException(BaseCustomException):
    def __init__(self, detail: str = "이메일 또는 비밀번호가 잘못되었습니다"):
        super().__init__(status_code=401, detail=detail, code=ErrorCode.INVALID_CREDENTIALS)


class TokenExpiredException(BaseCustomException):
    def __init__(self, detail: str = "토큰이 유효하지 않거나 만료되었습니다"):
        super().__init__(status_code=401, detail=detail, code=ErrorCode.TOKEN_EXPIRED)


class TokenForbiddenException(BaseCustomException):
    def __init__(self, detail: str = "잘못된 토큰입니다."):
        super().__init__(status_code=403, detail=detail, code=ErrorCode.TOKEN_FORBIDDEN)


class OAuthStateMismatchException(BaseCustomException):
    def __init__(self, detail: str = "유효하지 않은 OAuth 상태값입니다. (CSRF 공격 의심 또는 세션 만료)"):
        super().__init__(status_code=400, detail=detail, code=ErrorCode.INVALID_INPUT_VALUE)
