"""
[app.py] Gradio 챗봇 + FAQ 관리 - 완성형 (4,705건 + TF-IDF + share=True)
=========================================================================
Stage 3의 admin 기능 + Stage 5의 TF-IDF 검색을 합친 최종 버전.
- 챗봇 탭: TF-IDF로 4,705건에서 정확하게 검색
- FAQ 관리 탭: FAQ 추가/삭제 + 검색 필터

수정 포인트:
  [A1] FAQ 추가 후 TF-IDF 인덱스가 자동 재구축되는 것을 확인하세요
"""
from __future__ import annotations
import os
from pathlib import Path
import gradio as gr
from gemini import GeminiClient
from rag import answer_question, rebuild_index, get_faq_table, add_faq_entry, delete_faq_entry, get_faq_count


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


CERTS = [
    "한식조리기능사", "지게차운전기능사", "굴착기운전기능사", "전기기능사",
    "공인중개사", "손해평가사", "요양보호사", "위생사",
]


def do_add(cert, category, title, reply):
    if not title.strip() or not reply.strip():
        return "제목과 답변을 입력하세요", get_faq_table()
    add_faq_entry(cert, category.strip(), title.strip(), reply.strip())
    rebuild_index()
    return f"추가 완료 (총 {get_faq_count()}건, TF-IDF 재구축됨)", get_faq_table()


def do_delete(faq_id_str):
    if not faq_id_str.strip():
        return "삭제할 FAQ ID를 입력하세요", get_faq_table()
    try:
        faq_id = int(faq_id_str.strip())
    except ValueError:
        return "ID는 숫자여야 합니다", get_faq_table()
    delete_faq_entry(faq_id)
    rebuild_index()
    return f"삭제 완료 (총 {get_faq_count()}건, TF-IDF 재구축됨)", get_faq_table()


def do_search(query):
    return get_faq_table(query)


with gr.Blocks(title="MP1 - 자격증 FAQ 챗봇 (완성형)") as demo:

    with gr.Tab("챗봇"):
        gr.Markdown(f"## 자격증 시험 접수 FAQ 챗봇 (완성형)\n{get_faq_count()}건 FAQ + TF-IDF 검색 + Gemini 답변")
        chatbot = gr.ChatInterface(fn=chat, examples=[
            "한식조리기능사 시험비가 얼마예요?",
            "지게차 접수는 어디서 해요?",
            "전기기능사 계산기 반입 되나요?",
            "요양보호사 합격 기준이 몇 점이에요?",
            "공인중개사 환불 규정이 어떻게 되나요?",
            "굴착기 실기 준비물이 뭐예요?",
        ])

    with gr.Tab("FAQ 관리"):
        gr.Markdown(f"## FAQ 관리 ({get_faq_count()}건)\nFAQ를 추가/삭제하면 TF-IDF 인덱스가 자동 재구축됩니다.")

        with gr.Row():
            cert_input = gr.Dropdown(choices=CERTS, label="자격증", value="한식조리기능사")
            cat_input = gr.Textbox(label="카테고리", placeholder="예: 접수비, 합격기준, 환불")
        title_input = gr.Textbox(label="제목", placeholder="예: 한식조리기능사 준비물")
        reply_input = gr.Textbox(label="답변 내용", lines=3)
        add_btn = gr.Button("FAQ 추가", variant="primary")
        add_msg = gr.Textbox(label="결과", interactive=False)

        gr.Markdown("---")

        with gr.Row():
            delete_id = gr.Textbox(label="삭제할 FAQ ID (숫자)", placeholder="예: 4706")
            delete_btn = gr.Button("삭제", variant="stop")
        delete_msg = gr.Textbox(label="결과", interactive=False)

        gr.Markdown("---")
        search_input = gr.Textbox(label="검색 (자격증명/카테고리/제목)", placeholder="예: 요양보호사")
        search_btn = gr.Button("검색")
        faq_table = gr.Dataframe(
            value=get_faq_table(),
            headers=["ID", "자격증", "카테고리", "제목"],
            label="FAQ 목록 (최근 50건)",
        )

        add_btn.click(do_add, [cert_input, cat_input, title_input, reply_input], [add_msg, faq_table])
        delete_btn.click(do_delete, [delete_id], [delete_msg, faq_table])
        search_btn.click(do_search, [search_input], [faq_table])


if __name__ == "__main__":
    demo.launch(share=True)
