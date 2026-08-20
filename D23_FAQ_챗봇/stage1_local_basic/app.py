"""
[app.py] Gradio 챗봇 UI
========================
이 파일이 하는 일:
  1. .env 파일에서 API 키를 읽는다
  2. Gemini 클라이언트를 만든다
  3. 사용자 질문 -> rag.py로 FAQ 검색 -> Gemini가 답변 생성
  4. Gradio 웹 화면을 띄운다

수정 포인트:
  [A1] title, description을 본인 프로젝트에 맞게 바꾸세요
  [A2] examples에 본인이 테스트하고 싶은 질문을 추가하세요
  [A3] chat() 함수의 출력 포맷을 바꿔보세요 (예: 점수 표시 제거)
"""
from __future__ import annotations
import os
from pathlib import Path
import gradio as gr
from gemini import GeminiClient
from rag import answer_question


def load_env():
    """
    .env 파일에서 환경변수를 읽는다.
    GOOGLE_API_KEY=... 형태의 줄을 파싱해서 os.environ에 넣는다.
    """
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
    """
    Gradio가 사용자 메시지를 받으면 이 함수를 호출한다.
    message: 사용자가 입력한 텍스트
    history: 이전 대화 기록 (Gradio가 자동 관리)

    흐름: 질문 -> answer_question(검색+Gemini) -> 결과 문자열 반환
    """
    try:
        result = answer_question(message, client.generate)
        # [A3] 아래 포맷을 수정하면 챗봇 답변 모양이 바뀐다
        return f"[{result['status']}] {result['answer']}\n\n출처: {result['source']}"
    except Exception as error:
        return f"[ERROR] {type(error).__name__}: {error}"


# [A2] 여기에 테스트 질문을 추가/수정하세요
EXAMPLES = [
    "한식조리기능사 시험비가 얼마예요?",
    "지게차 접수는 어디서 해요?",
    "굴착기 시험 과목이 뭐예요?",
    "요양보호사 합격 기준이 몇 점이에요?",
    "공인중개사 환불 규정이 어떻게 되나요?",
    "위생사 응시 자격이 있나요?",
    "손해평가사 1차 2차 차이가 뭐예요?",
    "전기기능사 계산기 가져가도 되나요?",
]

# [A1] title과 description을 본인 프로젝트에 맞게 수정하세요
demo = gr.ChatInterface(
    fn=chat,
    title="MP1 - 자격증 시험 접수 FAQ 챗봇",
    description="8개 자격증 시험 접수 관련 문의에 답변합니다. (FAQ 검색 + Gemini 근거 답변)",
    examples=EXAMPLES,
)

if __name__ == "__main__":
    demo.launch()
