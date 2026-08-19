from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr


FAQ_PATH = Path(__file__).parent / "faq" / "faq.json"
FALLBACK_MESSAGE = "관련 내용을 FAQ에서 찾지 못했습니다. 고객센터로 문의해 주세요."


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


def answer_question(question: str, faq_items: List[Dict[str, str]] | None = None) -> str:
    question = question.strip()
    if not question:
        return "궁금한 내용을 입력해 주세요."

    items = faq_items if faq_items is not None else load_faq()
    query_tokens = tokens(question)
    best_item = None
    best_score = 0
    for item in items:
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

    if best_item is None:
        return FALLBACK_MESSAGE
    return f"{best_item['title']}\n{best_item['text']}"


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
            answer = gr.Textbox(label="답변", lines=5, interactive=False)
        with gr.Row():
            ask_button = gr.Button("답변 보기", variant="primary")
            clear_button = gr.ClearButton([question, answer], value="초기화")
        gr.Examples(
            examples=[[title] for title in choices],
            inputs=question,
            label="자주 찾는 질문",
        )
        ask_button.click(lambda value: answer_question(value, faq_items), question, answer)
        question.submit(lambda value: answer_question(value, faq_items), question, answer)

    return app


def run_tests() -> None:
    faq_items = load_faq()
    cases = [
        ("환불은 어떻게 되나요?", "환불 FAQ"),
        ("배송 조회는 어디서 하나요?", "배송 조회 FAQ"),
        ("배송지를 바꾸고 싶어요.", "배송지 변경 FAQ"),
        ("오늘 날씨가 어때요?", FALLBACK_MESSAGE),
        ("", "궁금한 내용을 입력해 주세요."),
    ]
    for question, expected in cases:
        actual = answer_question(question, faq_items)
        assert actual == expected or actual.startswith(expected + "\n"), (question, actual)
    print(f"FAQ 테스트 통과: {len(cases)}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gradio FAQ chatbot")
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
