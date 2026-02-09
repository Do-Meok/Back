import httpx
import uuid
import base64
import time

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
                response = await client.post(self.base_url, headers=headers, json=payload)

                response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise AITimeoutException()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise AIServiceException("AI 요청 한도를 초과했습니다. 잠시 후 시도해주세요.")
            if e.response.status_code == 401:
                raise AIServiceException("AI 인증에 실패했습니다. (API Key 확인 필요)")

            raise AIServiceException(f"OpenAI 에러 ({e.response.status_code}): {e.response.text}")

        except httpx.RequestError as e:
            raise AIConnectionException(f"네트워크 연결 오류: {str(e)}")

        except Exception as e:
            raise AIServiceException(f"AI Client 알 수 없는 오류: {str(e)}")


llm_client = LLMClient()


class OCRClient:
    def __init__(self):
        self.api_url = settings.NAVER_OCR_API_URL
        self.secret_key = settings.NAVER_OCR_SECRET_KEY.get_secret_value()
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def get_ocr_text(self, image_content: bytes, ext: str = "jpg") -> str:
        if not self.secret_key:
            raise AIServiceException(detail="Naver OCR Secret Key가 설정되지 않았습니다.")

        headers = {
            "X-OCR-SECRET": self.secret_key,
            "Content-Type": "application/json",
        }

        payload = self._make_payload(image_content, ext)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()

            return self._parse_response(response.json())

        except httpx.TimeoutException:
            raise AITimeoutException("OCR 서버 응답 시간이 초과되었습니다.")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AIServiceException("OCR 인증에 실패했습니다. (Secret Key 확인)")
            if e.response.status_code == 400:
                raise AIServiceException("잘못된 요청입니다. (이미지 포맷 확인)")

            raise AIServiceException(f"Naver OCR 에러 ({e.response.status_code}): {e.response.text}")

        except httpx.RequestError as e:
            raise AIConnectionException(f"네트워크 연결 오류: {str(e)}")

        except Exception as e:
            raise AIServiceException(f"OCR Client 알 수 없는 오류: {str(e)}")

    def _make_payload(self, image_content: bytes, ext: str) -> dict:
        image_data = base64.b64encode(image_content).decode("utf-8")

        return {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "images": [{"format": ext, "name": "domeok_scan", "data": image_data}],
        }

    def _parse_response(self, data: dict) -> str:
        parsed_texts = []
        try:
            images = data.get("images", [])
            for image in images:
                if image.get("inferResult") == "FAILURE":
                    continue

                fields = image.get("fields", [])
                for field in fields:
                    text = field.get("inferText", "")
                    if text:
                        parsed_texts.append(text)

            return " ".join(parsed_texts)

        except Exception:
            return ""


ocr_client = OCRClient()
