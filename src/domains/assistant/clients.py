import httpx

from core.config import settings
from domains.assistant.exceptions import (
    AIServiceException,
    AITimeoutException,
    AIConnectionException,
)


class LLMClient:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY.get_secret_value()
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini"
        self.max_tokens = 1000  # 최대 토큰값
        self.temperature = 0.7  # 창의성 설정(0~1)

        self.timeout = httpx.Timeout(50.0, connect=10.0)

    async def get_response(self, prompt: str) -> str:
        if not self.api_key:
            raise AIServiceException(detail="OpenAI API Key가 설정되지 않았습니다.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url, headers=headers, json=payload
                )

                response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise AITimeoutException()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise AIServiceException(
                    "AI 요청 한도를 초과했습니다. 잠시 후 시도해주세요."
                )
            if e.response.status_code == 401:
                raise AIServiceException("AI 인증에 실패했습니다. (API Key 확인 필요)")

            raise AIServiceException(
                f"OpenAI 에러 ({e.response.status_code}): {e.response.text}"
            )

        except httpx.RequestError as e:
            raise AIConnectionException(f"네트워크 연결 오류: {str(e)}")

        except Exception as e:
            raise AIServiceException(f"AI Client 알 수 없는 오류: {str(e)}")


llm_client = LLMClient()
