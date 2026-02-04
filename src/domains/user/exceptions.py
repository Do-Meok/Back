from core.exception.exceptions import BaseCustomException


class DuplicateEmailException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 이메일입니다"):
        super().__init__(status_code=409, detail=detail, code="EMAIL_CONFLICT")


class DuplicateNicknameException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 닉네임입니다"):
        super().__init__(status_code=409, detail=detail, code="NICKNAME_CONFLICT")


class DuplicatePhoneNumException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 전화번호입니다"):
        super().__init__(status_code=409, detail=detail, code="PHONE_NUM_CONFLICT")


class InvalidCheckedPasswordException(BaseCustomException):
    def __init__(self, detail: str = "비밀번호와 비밀번호 확인이 일치하지 않습니다"):
        super().__init__(status_code=400, detail=detail, code="PASSWORD_MISMATCH")


class UnauthorizedException(BaseCustomException):
    def __init__(self, detail: str = "로그인이 필요합니다"):
        super().__init__(status_code=401, detail=detail, code="UNAUTHORIZED")


class UserNotFoundException(BaseCustomException):
    def __init__(self, detail="해당 유저를 찾을 수 없습니다"):
        super().__init__(status_code=404, detail=detail, code="USER_NOT_FOUND")


class TokenExpiredException(BaseCustomException):
    def __init__(self, detail: str = "토큰이 유효하지 않거나 만료되었습니다"):
        super().__init__(status_code=401, detail=detail, code="TOKEN_EXPIRED")


class InvalidCredentialsException(BaseCustomException):
    def __init__(self, detail: str = "이메일 또는 비밀번호가 잘못되었습니다"):
        super().__init__(status_code=401, detail=detail, code="INVALID_CREDENTIALS")


class TokenForbiddenException(BaseCustomException):
    def __init__(self, detail: str = "해당 토큰에 대한 권한이 없습니다"):
        super().__init__(status_code=403, detail=detail, code="TOKEN_FORBIDDEN")


class IncorrectPasswordException(BaseCustomException):
    def __init__(self, detail: str = "현재 비밀번호가 잘못되었습니다"):
        super().__init__(status_code=401, detail=detail, code="INCORRECT_PASSWORD")


class PasswordUnchangedException(BaseCustomException):
    def __init__(self):
        super().__init__(status_code=400, detail="현재 비밀번호와 새 비밀번호가 같습니다.", code="PASSWORD_UNCHANGED")


class PasswordMismatchException(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=400, detail="변경할 비밀번호와 확인 비밀번호가 일치하지 않습니다.", code="PASSWORD_MISMATCH"
        )


class PasswordLengthException(BaseCustomException):
    def __init__(self):
        super().__init__(status_code=400, detail="비밀번호는 최소 8자에서 20자 사이여야 합니다.")
