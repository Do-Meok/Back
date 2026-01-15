import json
import re
from typing import Dict, Any, Union
from domains.assistant.exceptions import (
    AIJsonDecodeException,
    AINullResponseException,
    AIRefusalException,
)


class LLMParser:
    @staticmethod
    def parse(response_text: str) -> Union[Dict[str, Any], list[Any]]:
        if not response_text or not response_text.strip():
            raise AINullResponseException()

        clean_text = response_text.strip()
        match = re.search(r"```(json)?\s*([\s\S]+?)\s*```", clean_text)

        if match:
            clean_text = match.group(2).strip()

        try:
            parsed_data = json.loads(clean_text)

            if isinstance(parsed_data, dict) and "error" in parsed_data:
                raise AIRefusalException(detail=parsed_data["error"])

            return parsed_data

        except json.JSONDecodeError as e:
            raise AIJsonDecodeException(detail=f"AI 응답 파싱 실패: {str(e)}")
