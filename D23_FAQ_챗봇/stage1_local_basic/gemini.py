"""
[gemini.py] Gemini API 클라이언트
==================================
이 파일이 하는 일:
  1. GOOGLE_API_KEY 환경변수에서 API 키를 가져온다
  2. Gemini REST API에 프롬프트를 보내고 답변 텍스트를 받는다

수정 포인트:
  [G1] 모델명을 바꿔보세요 (gemini-2.5-flash-lite -> gemini-2.5-flash 등)
  [G2] timeout 값을 조정해보세요 (느린 네트워크에서는 30 -> 60)
"""
from __future__ import annotations
import json
import os
import urllib.request


def _default_transport(url, payload, headers, timeout):
    """urllib로 HTTP POST 요청을 보낸다. 외부 라이브러리(requests) 없이 동작."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class GeminiClient:
    def __init__(self, api_key=None, model=None, transport=None):
        # API 키: .env에서 읽거나 직접 전달
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        # [G1] 모델명 변경 - .env의 GEMINI_MODEL로도 바꿀 수 있다
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.transport = transport or _default_transport

    def generate(self, prompt):
        """
        프롬프트를 Gemini에 보내고 답변 텍스트를 반환한다.

        prompt: 문자열 (rag.py의 build_prompt가 만든 전체 프롬프트)
        return: Gemini가 생성한 답변 문자열
        """
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY가 없습니다. .env 파일에 키를 넣어주세요.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        # [G2] timeout=30 -> 네트워크 느리면 60으로
        data = self.transport(url, payload, headers, 30)

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Gemini 응답에서 답변 텍스트를 찾지 못했습니다.") from error
