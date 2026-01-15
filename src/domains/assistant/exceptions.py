from core.exception.exceptions import BaseCustomException


class AIServiceException(BaseCustomException):
    def __init__(self, detail: str = "AI 서비스 연결 중 오류가 발생했습니다."):
        super().__init__(status_code=503, detail=detail, code="AI_SERVICE_ERROR")


class AIConnectionException(BaseCustomException):
    def __init__(self, detail: str = "AI 서버와 연결할 수 없습니다."):
        super().__init__(status_code=503, detail=detail, code="AI_CONNECTION_ERROR")


class AITimeoutException(BaseCustomException):
    def __init__(self, detail: str = "AI 응답 시간이 초과되었습니다."):
        super().__init__(status_code=504, detail=detail, code="AI_TIMEOUT_ERROR")


class AINullResponseException(BaseCustomException):
    def __init__(self, detail: str = "AI로부터 빈 응답을 받았습니다."):
        super().__init__(status_code=500, detail=detail, code="AI_NULL_RESPONSE")


class AIJsonDecodeException(BaseCustomException):
    def __init__(self, detail: str = "AI 응답을 분석하는 데 실패했습니다."):
        super().__init__(status_code=500, detail=detail, code="AI_JSON_PARSE_ERROR")


class AISchemaMismatchException(BaseCustomException):
    def __init__(self, detail: str = "AI 응답 형식이 올바르지 않습니다."):
        super().__init__(status_code=500, detail=detail, code="AI_SCHEMA_ERROR")


class InvalidAIRequestException(BaseCustomException):
    def __init__(self, detail: str = "잘못된 요청입니다."):
        super().__init__(status_code=400, detail=detail, code="AI_INVALID_REQUEST")


class AIRefusalException(BaseCustomException):
    def __init__(self, detail: str = "AI가 요청을 처리할 수 없습니다."):
        super().__init__(status_code=400, detail=detail, code="AI_REFUSAL_ERROR")
