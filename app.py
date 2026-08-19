from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 추가
from dotenv import load_dotenv

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr
import google.generativeai as genai

# 추가: .env 로드 (프로젝트 루트 기준)
# - override=False: 이미 OS 환경변수에 설정된 값이 있으면 그걸 우선 사용
load_dotenv(override=False)


FAQ_PATH = Path(__file__).parent / "faq" / "faq.json"
FALLBACK_MESSAGE = "관련 내용을 FAQ에서 찾지 못했습니다. 고객센터로 문의해 주세요."


# -----------------------------
# FAQ 로딩/검색(기존 유지)
# -----------------------------
def load_faq() -> List[Dict[str, str]]:
    with FAQ_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("faq.json은 배열이어야 합니다.")
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not isinstance(item.get("text"), str):
            raise ValueError("FAQ 항목은 title과 text 문자열을 가져야 합니다.")
    return data


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[가-힣A-Za-z0-9]{2,}", value.lower()))


def find_best_faq(question: str, faq_items: List[Dict[str, str]]) -> Tuple[Optional[Dict[str, str]], int]:
    """FAQ에서 가장 유사한 항목과 점수를 반환."""
    query_tokens = tokens(question)
    best_item = None
    best_score = 0

    for item in faq_items:
        title_tokens = tokens(item["title"])
        body_tokens = tokens(item["text"])

        title_score = sum(
            max(
                (len(item_token) for item_token in title_tokens if query_token in item_token or item_token in query_token),
                default=0,
            )
            for query_token in query_tokens
        )

        body_score = sum(
            1
            for query_token in query_tokens
            if any(query_token in item_token or item_token in query_token for item_token in body_tokens)
        )

        score = title_score * 3 + body_score
        if score > best_score:
            best_item = item
            best_score = score

    return best_item, best_score


# -----------------------------
# Gemini 연동
# -----------------------------
def gemini_answer(question: str, faq_items: List[Dict[str, str]]) -> str:
    """
    FAQ 내용을 참고 컨텍스트로 넣되,
    'FAQ 기반 자격증 안내' 톤으로 답변하게 하는 간단한 RAG 스타일 프롬프트.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        # 키가 없으면 생성 답변 불가 → 기존 폴백
        return FALLBACK_MESSAGE

    genai.configure(api_key=api_key)

    # 모델은 필요에 맞게 변경 가능
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    model = genai.GenerativeModel(model_name)

    # FAQ를 컨텍스트로 제공 (너무 길면 상위 N개만 추리거나 요약하는 방식 권장)
    # 여기서는 간단히 전체를 넣되, 운영에서는 길이 관리하세요.
    faq_context_lines = []
    for i, item in enumerate(faq_items, start=1):
        faq_context_lines.append(f"[{i}] {item['title']}\n{item['text']}")
    faq_context = "\n\n".join(faq_context_lines)

    system_style = (
        "너는 '자격증 과정/응시/환불/배송 등'에 대한 고객 FAQ 상담원이다. "
        "답변은 한국어로, 친절하지만 과장 없이, 핵심 위주로 작성한다. "
        "가능하면 아래 FAQ 컨텍스트 근거를 바탕으로 답하고, "
        "FAQ에 없는 내용이면 '확인 필요/고객센터 문의'를 안내한다. "
        "절대로 사실을 임의로 만들어내지 말라."
    )

    prompt = f"""[역할 지침]
{system_style}

[FAQ 컨텍스트]
{faq_context}

[사용자 질문]
{question}

[답변 형식]
- 2~6문장 내로 간결하게
- 필요한 경우 bullet 사용 가능
- 마지막에 다음 중 하나를 포함:
  - "추가로 필요한 정보가 있으면 질문해 주세요."
  - 또는 "정확한 확인을 위해 고객센터로 문의해 주세요."
"""

    try:
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 512,
            },
        )
        text = (resp.text or "").strip()
        return text if text else FALLBACK_MESSAGE
    except Exception:
        # 운영에서는 로깅 권장
        return FALLBACK_MESSAGE


# -----------------------------
# 최종 답변 함수 (FAQ → Gemini)
# -----------------------------
def answer_question(
    question: str,
    faq_items: List[Dict[str, str]] | None = None,
    *,
    use_gemini: bool = True,
    min_faq_score: int = 2,
) -> str:
    question = question.strip()
    if not question:
        return "궁금한 내용을 입력해 주세요."

    items = faq_items if faq_items is not None else load_faq()

    best_item, best_score = find_best_faq(question, items)

    # FAQ 점수가 충분하면 FAQ 답변
    if best_item is not None and best_score >= min_faq_score:
        return f"{best_item['title']}\n{best_item['text']}"

    # FAQ로 못 찾았으면 Gemini로 생성(옵션)
    if use_gemini:
        return gemini_answer(question, items)

    return FALLBACK_MESSAGE


def build_app() -> gr.Blocks:
    faq_items = load_faq()
    choices = [item["title"] for item in faq_items]

    with gr.Blocks(title="FAQ 안내") as app:
        gr.Markdown("# 자격증 FAQ 안내\n궁금한 내용을 편하게 입력해 주세요.")
        with gr.Row():
            question = gr.Textbox(
                label="질문",
                placeholder="예: 환불은 어떻게 되나요?",
                lines=2,
            )
            answer = gr.Textbox(label="답변", lines=7, interactive=False)

        with gr.Row():
            ask_button = gr.Button("답변 보기", variant="primary")
            clear_button = gr.ClearButton([question, answer], value="초기화")

        with gr.Accordion("옵션", open=False):
            use_gemini = gr.Checkbox(value=True, label="FAQ에 없으면 Gemini로 답변 생성")
            min_faq_score = gr.Slider(
                minimum=0, maximum=20, value=2, step=1,
                label="FAQ 매칭 최소 점수(이하면 Gemini로 넘어감)"
            )

        gr.Examples(
            examples=[[title] for title in choices],
            inputs=question,
            label="자주 찾는 질문",
        )

        def _do_answer(q: str, use_g: bool, min_score: int) -> str:
            return answer_question(q, faq_items, use_gemini=use_g, min_faq_score=min_score)

        ask_button.click(_do_answer, [question, use_gemini, min_faq_score], answer)
        question.submit(_do_answer, [question, use_gemini, min_faq_score], answer)

    return app


def run_tests() -> None:
    faq_items = load_faq()
    cases = [
        ("환불은 어떻게 되나요?", "환불 FAQ"),
        ("배송 조회는 어디서 하나요?", "배송 조회 FAQ"),
        ("배송지를 바꾸고 싶어요.", "배송지 변경 FAQ"),
        ("오늘 날씨가 어때요?", FALLBACK_MESSAGE),  # Gemini 켜면 이 케이스는 바뀔 수 있음
        ("", "궁금한 내용을 입력해 주세요."),
    ]

    for question, expected in cases:
        actual = answer_question(question, faq_items, use_gemini=False)  # 테스트는 FAQ만
        assert actual == expected or actual.startswith(expected + "\n"), (question, actual)

    print(f"FAQ 테스트 통과: {len(cases)}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gradio FAQ chatbot (+Gemini)")
    parser.add_argument("--test", action="store_true", help="FAQ 응답 테스트 실행")
    parser.add_argument("--share", action="store_true", help="Gradio 공유 URL 생성")
    args = parser.parse_args()

    if args.test:
        run_tests()
    else:
        port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
        build_app().launch(
            server_name="127.0.0.1",
            server_port=port,
            share=args.share,
        )