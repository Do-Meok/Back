from enum import Enum


class ErrorCode(str, Enum):
    # ----------------------------------------
    # 1. Common / Global (공통)
    # ----------------------------------------
    NOT_FOUND = "NOT_FOUND"  # 데이터 없음 (범용)
    INVALID_INPUT_VALUE = "INVALID_INPUT_VALUE"  # 유효하지 않은 입력 (범용)
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 요청 본문/쿼리 파라미터 검증 실패
    UNAUTHORIZED = "UNAUTHORIZED"  # 인증 필요 (로그인 안함)
    HTTP_ERROR = "HTTP_ERROR"  # 프레임워크 기본 HTTP 예외
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"  # 서버 내부 에러

    # ----------------------------------------
    # 2. Auth & Token (인증/인가)
    # ----------------------------------------
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"  # 아이디 또는 비밀번호 틀림
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # 토큰 만료
    TOKEN_FORBIDDEN = "TOKEN_FORBIDDEN"  # 토큰 권한 없음 (위변조 등)

    # ----------------------------------------
    # 3. User (회원)
    # ----------------------------------------
    USER_NOT_FOUND = "USER_NOT_FOUND"  # 유저 찾을 수 없음
    EMAIL_CONFLICT = "EMAIL_CONFLICT"  # 이메일 중복
    NICKNAME_CONFLICT = "NICKNAME_CONFLICT"  # 닉네임 중복
    PHONE_NUM_CONFLICT = "PHONE_NUM_CONFLICT"  # 전화번호 중복

    PASSWORD_MISMATCH = "PASSWORD_MISMATCH"  # 비밀번호 확인 불일치 (가입/변경 시)
    INCORRECT_PASSWORD = "INCORRECT_PASSWORD"  # 현재 비밀번호 틀림 (변경 시)
    PASSWORD_UNCHANGED = "PASSWORD_UNCHANGED"  # 변경하려는 비번이 기존과 동일

    # ----------------------------------------
    # 4. Ingredient (식재료)
    # ----------------------------------------
    INGREDIENT_NOT_FOUND = "INGREDIENT_NOT_FOUND"  # 식재료 없음
    VALUE_NOT_FOUND = "VALUE_NOT_FOUND"  # 필수 값(유통기한/보관장소) 누락
    COMPARTMENT_NOT_FOUND = "COMPARTMENT_NOT_FOUND"  # 냉장고 칸 없음
    INVALID_INGREDIENT = "INVALID_INGREDIENT"  # 등록 불가 식재료 포함

    # ----------------------------------------
    # 5. Recipe (레시피)
    # ----------------------------------------
    RECIPE_DATA_CORRUPTION = "RECIPE_DATA_CORRUPTION"  # 레시피 데이터 손상

    # ----------------------------------------
    # 6. Refrigerator (냉장고)
    # ----------------------------------------
    REFRIGERATOR_NOT_FOUND = "REFRIGERATOR_NOT_FOUND"  # 냉장고 없음

    # ----------------------------------------
    # 7. Shopping (장보기/아이템)
    # ----------------------------------------
    ITEM_NOT_FOUND = "ITEM_NOT_FOUND"  # 아이템 없음

    # ----------------------------------------
    # 8. AI Service (인공지능)
    # ----------------------------------------
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"  # AI 서비스 연결 오류 (503)
    AI_CONNECTION_ERROR = "AI_CONNECTION_ERROR"  # AI 서버 연결 불가
    AI_TIMEOUT_ERROR = "AI_TIMEOUT_ERROR"  # AI 응답 시간 초과
    AI_NULL_RESPONSE = "AI_NULL_RESPONSE"  # AI 응답이 비어있음
    AI_JSON_PARSE_ERROR = "AI_JSON_PARSE_ERROR"  # AI 응답 파싱 실패
    AI_SCHEMA_ERROR = "AI_SCHEMA_ERROR"  # AI 응답 형식 불일치
    AI_INVALID_REQUEST = "AI_INVALID_REQUEST"  # 잘못된 AI 요청
    AI_REFUSAL_ERROR = "AI_REFUSAL_ERROR"  # AI가 답변 거부
