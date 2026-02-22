from core.exception.errors import ErrorCode
from core.exception.exceptions import BaseCustomException


class DuplicateEmailException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 이메일입니다"):
        super().__init__(status_code=409, detail=detail, code=ErrorCode.EMAIL_CONFLICT)


class DuplicateNicknameException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 닉네임입니다"):
        super().__init__(status_code=409, detail=detail, code=ErrorCode.NICKNAME_CONFLICT)


class DuplicatePhoneNumException(BaseCustomException):
    def __init__(self, detail: str = "이미 사용 중인 전화번호입니다"):
        super().__init__(status_code=409, detail=detail, code=ErrorCode.PHONE_NUM_CONFLICT)


class InvalidCheckedPasswordException(BaseCustomException):
    def __init__(self, detail: str = "비밀번호와 비밀번호 확인이 일치하지 않습니다"):
        super().__init__(status_code=400, detail=detail, code=ErrorCode.PASSWORD_MISMATCH)


class UnauthorizedException(BaseCustomException):
    def __init__(self, detail: str = "로그인이 필요합니다"):
        super().__init__(status_code=401, detail=detail, code=ErrorCode.UNAUTHORIZED)


class UserNotFoundException(BaseCustomException):
    def __init__(self, detail: str = "해당 유저를 찾을 수 없습니다"):
        super().__init__(status_code=404, detail=detail, code=ErrorCode.USER_NOT_FOUND)


class IncorrectPasswordException(BaseCustomException):
    def __init__(self, detail: str = "현재 비밀번호가 잘못되었습니다"):
        super().__init__(status_code=401, detail=detail, code=ErrorCode.INCORRECT_PASSWORD)


class PasswordUnchangedException(BaseCustomException):
    def __init__(self, detail: str = "현재 비밀번호와 새 비밀번호가 같습니다."):
        super().__init__(status_code=400, detail=detail, code=ErrorCode.PASSWORD_UNCHANGED)


class PasswordMismatchException(BaseCustomException):
    def __init__(self, detail: str = "변경할 비밀번호와 확인 비밀번호가 일치하지 않습니다."):
        super().__init__(status_code=400, detail=detail, code=ErrorCode.PASSWORD_MISMATCH)
