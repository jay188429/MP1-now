"""
[app.py] Gradio 챗봇 UI - TF-IDF 검색 (4,705건)
=================================================
Stage 4에서 키워드 매칭의 한계를 확인했다면,
이 단계에서는 TF-IDF로 검색 품질을 개선한다.

수정 포인트:
  [A1] title, description을 본인 프로젝트에 맞게 바꾸세요
  [A2] examples에 본인이 테스트하고 싶은 질문을 추가하세요
"""
from __future__ import annotations
import os
from pathlib import Path
import gradio as gr
from gemini import GeminiClient
from rag import answer_question


def load_env():
    path = Path(__file__).resolve().parent / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()
client = GeminiClient()


def chat(message, history):
    try:
        result = answer_question(message, client.generate)
        return f"[{result['status']}] {result['answer']}\n\n출처: {result['source']} (유사도: {result['score']:.2f})"
    except Exception as error:
        return f"[ERROR] {type(error).__name__}: {error}"


EXAMPLES = [
    "한식조리기능사 시험비가 얼마예요?",
    "지게차 접수는 어디서 해요?",
    "전기기능사 계산기 반입 되나요?",
    "요양보호사 합격 기준이 몇 점이에요?",
    "공인중개사 환불 규정이 어떻게 되나요?",
    "위생사 응시 자격이 있나요?",
    "손해평가사 접수 기간이 언제예요?",
    "굴착기 실기시험 준비물이 뭐예요?",
]

demo = gr.ChatInterface(
    fn=chat,
    title="MP1 - 자격증 FAQ 챗봇 (TF-IDF 검색)",
    description="4,705건 FAQ를 TF-IDF로 검색합니다. Stage 4의 키워드 매칭과 비교해보세요.",
    examples=EXAMPLES,
)

if __name__ == "__main__":
    demo.launch()
