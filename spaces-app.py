#!/usr/bin/env python3
"""
Hugging Face Spaces 배포용 Gradio 앱
Stage 6: TF-IDF 검색 + FAQ 관리 + Gemini
"""

import os
import json
import re
from pathlib import Path
import gradio as gr
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 환경 변수
API_KEY = os.getenv('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')

# FAQ 데이터
FAQ = []
vectorizer = None
tfidf_matrix = None

SYNONYMS_DICT = {
    "포크레인": "굴착기",
    "포클레인": "굴착기",
    "요보사": "요양보호사",
    "한조기": "한식조리기능사",
    "개사": "공인중개사",
    "공개사": "공인중개사",
    "손평사": "손해평가사",
    "지게차면허": "지게차운전기능사",
    "전기기사": "전기기능사"
}

def expand_synonyms(text):
    """동의어 확장"""
    expanded = text
    for short, full in SYNONYMS_DICT.items():
        expanded = re.sub(short, full, expanded, flags=re.IGNORECASE)
    return expanded

def load_faq_from_url():
    """온라인에서 FAQ 로드"""
    global FAQ, vectorizer, tfidf_matrix
    try:
        response = requests.get('https://mp1-now.vercel.app/faq_combined.jsonl', timeout=10)
        if response.status_code == 200:
            FAQ = [
                json.loads(line)
                for line in response.text.strip().split('\n')
                if line.strip()
            ]

            # TF-IDF 벡터화
            docs = [
                f"{row.get('cert', '')} {row.get('category', '')} {row.get('title', '')} {row.get('body', '')} {row.get('reply', '')}"
                for row in FAQ
            ]
            vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3), max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(docs)

            return True
    except Exception as e:
        print(f"FAQ 로드 오류: {e}")
    return False

def retrieve(question, top_k=3, min_score=0.01):
    """TF-IDF 검색"""
    if not FAQ or vectorizer is None:
        return []

    expanded_q = expand_synonyms(question)
    try:
        q_vec = vectorizer.transform([expanded_q])
        scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
        top_indices = scores.argsort()[::-1][:top_k]
        return [(float(scores[i]), FAQ[i]) for i in top_indices if scores[i] >= min_score]
    except:
        return []

def call_gemini(prompt):
    """Gemini API 호출"""
    if not API_KEY:
        return "⚠️ Gemini API 키가 설정되지 않았습니다"

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
    try:
        response = requests.post(url, json={
            'contents': [{
                'parts': [{'text': prompt}]
            }]
        }, headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': API_KEY
        }, timeout=30)

        if response.status_code != 200:
            return f"❌ API 오류 ({response.status_code})"

        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return f"❌ 오류: {str(e)}"

def build_prompt(question, document):
    """Gemini 프롬프트"""
    reply = document.get('reply', document.get('text', ''))
    return f"""당신은 자격증 시험 접수 FAQ 상담원입니다.
아래 근거 안에서만 답하세요. 근거에 없는 내용을 만들지 마세요.
근거로 답할 수 없으면 정확히 UNKNOWN이라고 답하세요.

[질문]
{question}

[근거]
{reply}

한국어 두 문장 이내로 답하세요."""

def chat(message, history):
    """챗봇 함수"""
    if not FAQ:
        return "⚠️ FAQ 데이터를 로드할 수 없습니다"

    results = retrieve(message)
    if not results:
        return "제공된 FAQ에서 확인할 수 없는 내용입니다."

    best_score, best_doc = results[0]

    generated = call_gemini(build_prompt(message, best_doc))

    if "UNKNOWN" in generated or "API" in generated or "오류" in generated:
        return f"제공된 FAQ에서 확인할 수 없는 내용입니다.\n\n📌 참고: {best_doc.get('title', '?')}"

    return f"{generated}\n\n📌 출처: {best_doc.get('cert', '?')} - {best_doc.get('title', '?')} (유사도: {best_score:.2f})"

def get_faq_table(query=""):
    """FAQ 테이블"""
    if not query:
        return [[f.get('id', '?'), f.get('cert', '?'), f.get('category', '?'), f.get('title', '?')] for f in FAQ[-50:]]

    query = query.lower()
    filtered = [
        [f.get('id', '?'), f.get('cert', '?'), f.get('category', '?'), f.get('title', '?')]
        for f in FAQ
        if any(query in str(f.get(k, '')).lower() for k in ['cert', 'category', 'title'])
    ]
    return filtered[:50]

def add_faq(cert, category, title, reply):
    """FAQ 추가"""
    if not title.strip() or not reply.strip():
        return "⚠️ 제목과 답변은 필수입니다", get_faq_table()

    new_id = max([f.get('id', 0) for f in FAQ], default=0) + 1
    FAQ.append({
        'id': new_id,
        'cert': cert,
        'category': category,
        'title': title.strip(),
        'body': '',
        'reply': reply.strip(),
        'channel': 'admin'
    })

    return f"✅ FAQ 추가 완료 (총 {len(FAQ)}건)\n💾 GitHub에 커밋하면 영속 저장됩니다", get_faq_table()

def delete_faq(faq_id_str):
    """FAQ 삭제"""
    if not faq_id_str.strip():
        return "⚠️ FAQ ID를 입력하세요", get_faq_table()

    try:
        faq_id = int(faq_id_str.strip())
    except ValueError:
        return "⚠️ ID는 숫자여야 합니다", get_faq_table()

    global FAQ
    before = len(FAQ)
    FAQ = [f for f in FAQ if f.get('id') != faq_id]

    if len(FAQ) == before:
        return f"⚠️ FAQ ID {faq_id}를 찾을 수 없습니다", get_faq_table()

    return f"✅ FAQ 삭제 완료 (총 {len(FAQ)}건)", get_faq_table()

def search_faq(query):
    """FAQ 검색"""
    return get_faq_table(query)

# FAQ 로드
load_faq_from_url()

# Gradio UI
CERTS = ["한식조리기능사", "지게차운전기능사", "굴착기운전기능사", "전기기능사",
         "공인중개사", "손해평가사", "요양보호사", "위생사"]

with gr.Blocks(title="MP1 - 자격증 FAQ 챗봇") as demo:

    with gr.Tab("🤖 챗봇"):
        gr.Markdown(f"## 자격증 시험 접수 FAQ 챗봇\n**{len(FAQ)}건 FAQ** • TF-IDF 검색 • Gemini 답변")
        chatbot = gr.ChatInterface(fn=chat, examples=[
            "한식조리기능사 응시료?",
            "지게차 접수는 어디서?",
            "전기기능사 계산기 반입 가능?",
            "요양보호사 합격 기준?",
            "공인중개사 환불 규정?",
        ])

    with gr.Tab("⚙️ FAQ 관리"):
        gr.Markdown(f"## FAQ 관리\n**총 {len(FAQ)}건** - 추가/삭제/검색")

        with gr.Row():
            cert_input = gr.Dropdown(choices=CERTS, label="자격증", value="한식조리기능사")
            cat_input = gr.Textbox(label="카테고리", placeholder="접수비, 합격기준, 환불")

        title_input = gr.Textbox(label="제목", placeholder="예: 한식조리기능사 응시료")
        reply_input = gr.Textbox(label="답변", lines=3)
        add_btn = gr.Button("➕ FAQ 추가", variant="primary")
        add_msg = gr.Textbox(label="결과", interactive=False)

        gr.Markdown("---")

        with gr.Row():
            delete_id = gr.Textbox(label="삭제할 ID", placeholder="예: 4706")
            delete_btn = gr.Button("🗑️ 삭제", variant="stop")
        delete_msg = gr.Textbox(label="결과", interactive=False)

        gr.Markdown("---")

        search_input = gr.Textbox(label="🔍 검색", placeholder="자격증명/카테고리/제목")
        search_btn = gr.Button("검색")
        faq_table = gr.Dataframe(
            value=get_faq_table(),
            headers=["ID", "자격증", "카테고리", "제목"],
            label="FAQ 목록 (최근 50건)"
        )

        add_btn.click(add_faq, [cert_input, cat_input, title_input, reply_input], [add_msg, faq_table])
        delete_btn.click(delete_faq, [delete_id], [delete_msg, faq_table])
        search_btn.click(search_faq, [search_input], [faq_table])

if __name__ == "__main__":
    demo.launch(share=True)
