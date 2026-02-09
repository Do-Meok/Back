import json
from typing import List, Dict, Any


class PromptBuilder:
    # 1. [메뉴 추천] 재료 목록 -> 메뉴 6개 추천
    @staticmethod
    def build_suggestion_prompt(user_ingredients: List[str]) -> str:
        return f"""
        당신은 전문 요리사 AI입니다. 사용자가 보유한 재료를 최대한 활용하여 만들 수 있는 요리 4가지를 추천하세요.

        사용 가능한 재료 목록:
        {json.dumps(user_ingredients, ensure_ascii=False)}

        필수 조건:
        - 출력은 반드시 JSON 본문만 포함해야 하며, 설명 텍스트나 코드 블록(예: ```json)은 절대 포함하지 마세요.
        - 출력 루트는 {{"recipes": [...]}} 형태여야 하며, recipes 배열의 길이는 정확히 4이어야 합니다.
        - 각 항목은 다음 키를 반드시 포함해야 합니다:
          - "food": 문자열. 대중적으로 인식되는 실제 요리명.
          - "use_ingredients": 문자열 배열. 사용자가 제공한 재료 중 사용된 것만 포함.
          - "difficulty": 1 이상 5 이하의 정수.
        - 기본 조미료(소금, 설탕, 간장 등)는 "use_ingredients"에 기재하지 마세요.
        - 동일하거나 유사한 요리명은 피하고, 조리법(찜, 구이, 탕 등)을 다양하게 구성하세요.
        - 식재료로 쓸 수 없는 항목이 있다면 {{"error": "..."}} JSON을 반환하세요.

        올바른 출력 예시:
        {{
          "recipes": [
            {{
              "food": "참치 토마토 오픈 샌드위치",
              "use_ingredients": ["빵", "참치", "토마토"],
              "difficulty": 2
            }},
            {{
              "food": "오징어 볶음 스파게티",
              "use_ingredients": ["오징어", "토마토"],
              "difficulty": 4
            }}
          ]
        }}
        """

    # 2. [상세 레시피] 요리명 + 재료 -> 상세 조리법 (Detail)
    @staticmethod
    def build_recipe_prompt(food: str, ingredients: List[Dict[str, Any]]) -> str:
        return f"""
        당신은 전문 요리사 AI입니다. 사용자가 요청한 음식의 상세 조리법을 JSON으로만 제공합니다.

        요청된 음식: {food}
        사용 가능한 재료: {json.dumps(ingredients, ensure_ascii=False)}

        필수 조건:
        - 반드시 요청된 음식명("{food}")의 레시피만 작성하세요.
        - "use_ingredients"에는 제공된 재료만 포함하며, 각 객체는 "name", "amount" 키를 가져야 합니다.
        - "steps"는 최소 3단계 이상으로 작성하되, 각 단계는 명확하고 간결하게 작성하세요.
        - 출력은 오직 JSON 본문만 포함하세요. (설명, 마크다운 금지)

        출력 스키마:
        {{
          "food": 문자열,
          "use_ingredients": [{{"name": 문자열, "amount": 문자열}}, ...],
          "steps": [문자열, ...],
          "tip": 문자열
        }}

        올바른 출력 예시:
        {{
          "food": "계란 오믈렛",
          "use_ingredients": [
            {{"name": "계란", "amount": "2개"}},
            {{"name": "양파", "amount": "50g"}}
          ],
          "steps": [
            "양파를 잘게 썰어 준비합니다.",
            "볼에 계란을 풀고 양파를 섞습니다.",
            "팬에 붓고 익혀 완성합니다."
          ],
          "tip": "우유를 넣으면 더 부드럽습니다."
        }}
        """

    # 3. [퀵 레시피] 재료 문자열 -> 요리 1개 추천 및 상세 (Quick)
    @staticmethod
    def build_quick_prompt(chat: str) -> str:
        return f"""
        당신은 요리 전문가 AI입니다. 입력된 재료만으로 만들 수 있는 최적의 요리 1가지를 추천하고 상세 레시피를 JSON으로 출력하세요.

        입력된 재료: "{chat}"

        필수 조건:
        - 제공된 재료 외의 주재료는 사용하지 마세요 (기본 조미료 제외).
        - JSON 형식만 출력하세요. (마크다운 금지)
        - "steps"는 최소 3단계 이상 작성하세요.

        출력 스키마:
        {{
          "food": 문자열,
          "use_ingredients": [{{"name": 문자열, "amount": 문자열}}, ...],
          "steps": [문자열, ...],
          "tip": 문자열
        }}
        """

    # 4. [검색 레시피] 요리명 문자열 -> 상세 레시피 (Search)
    @staticmethod
    def build_search_prompt(chat: str) -> str:
        return f"""
        당신은 요리 전문가 AI입니다. 입력된 음식명에 대한 정확한 레시피를 JSON으로 제공하세요.

        입력된 음식명: "{chat}"

        필수 조건:
        - 해당 음식에 대한 정확한 레시피여야 합니다.
        - JSON 본문만 출력하세요.

        만약 음식이 아니거나 모르는 요리라면 다음 JSON을 출력하세요:
        {{"error": "정확한 음식명을 입력해 주세요."}}

        출력 스키마:
        {{
          "food": 문자열,
          "use_ingredients": [{{"name": 문자열, "amount": 문자열}}, ...],
          "steps": [문자열, ...],
          "tip": 문자열
        }}
        """

    @staticmethod
    def build_receipt_parsing_prompt(ocr_text: str) -> str:
        return f"""
            당신은 영수증 데이터 분석 전문가 AI입니다. 아래 제공된 텍스트는 영수증을 OCR로 읽어들인 결과입니다.
            이 텍스트에서 '식재료(음식 재료)'에 해당하는 항목만 추출하여 JSON으로 반환하세요.
    
            분석할 OCR 텍스트:
            "{ocr_text}"
    
            필수 조건:
            1. 상호명, 주소, 전화번호, 가격, 결제 정보, 날짜, '봉투', '할인' 같은 비식재료 텍스트는 모두 무시하세요.
            2. 오로지 요리에 사용할 수 있는 식재료 이름만 추출하세요. (예: "콩나물 1봉" -> "콩나물", "서울우유 1L" -> "우유")
            3. 수량이나 규격은 제외하고 재료의 '이름'만 남기세요.
            4. 식재료가 하나도 없다면 빈 배열을 반환하세요.
            5. 출력은 오직 JSON 본문만 포함하세요. (코드 블록이나 설명 금지)
    
            출력 스키마:
            {{
              "ingredients": [문자열, 문자열, ...]
            }}
    
            올바른 출력 예시:
            {{
              "ingredients": ["삼겹살", "상추", "쌈장", "마늘"]
            }}
            """
