"""
[rag.py] FAQ 검색 + TF-IDF + FAQ CRUD - 완성형
================================================
Stage 5의 TF-IDF 검색 + Stage 3의 FAQ CRUD를 합친 최종 버전.
FAQ를 추가/삭제하면 TF-IDF 인덱스가 자동 재구축된다.

수정 포인트:
  [R1] min_score를 조정해서 검색 결과 변화를 관찰하세요 (TF-IDF는 0~1 범위)
  [R2] top_k를 늘려서 Gemini에게 여러 근거를 주어보세요
"""
from __future__ import annotations
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT.parent / "data" / "faq_combined.jsonl"
UNKNOWN = "제공된 FAQ에서 확인할 수 없는 내용입니다."


def _load_jsonl(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


FAQ = _load_jsonl(DATA_PATH)


def _build_docs(faq_list):
    return [
        f"{r.get('cert', '')} {r.get('category', '')} {r.get('title', '')} {r.get('body', '')} {r.get('reply', '')}"
        for r in faq_list
    ]


vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(_build_docs(FAQ))


def rebuild_index():
    """FAQ 변경 후 TF-IDF 인덱스를 재구축한다."""
    global vectorizer, tfidf_matrix
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(_build_docs(FAQ))


def get_faq_count():
    return len(FAQ)


def get_faq_table(query=""):
    """FAQ 목록을 테이블 형태로 반환한다 (최근 50건)."""
    filtered = FAQ
    if query:
        q = query.lower()
        filtered = [r for r in FAQ if
                     q in r.get("cert", "").lower() or
                     q in r.get("category", "").lower() or
                     q in r.get("title", "").lower()]
    rows = [[r.get("id", "?"), r.get("cert", ""), r.get("category", ""), r.get("title", "")] for r in filtered[-50:]]
    return rows


def add_faq_entry(cert, category, title, reply):
    """FAQ 항목을 추가한다."""
    max_id = max((r.get("id", 0) for r in FAQ), default=0)
    if isinstance(max_id, str):
        max_id = len(FAQ)
    entry = {
        "id": max_id + 1,
        "channel": "admin",
        "caller_type": "admin",
        "cert": cert,
        "category": category,
        "title": title,
        "body": title,
        "reply": reply,
        "resolution": "admin_added",
    }
    FAQ.append(entry)


def delete_faq_entry(faq_id):
    """FAQ 항목을 삭제한다."""
    global FAQ
    FAQ = [r for r in FAQ if r.get("id") != faq_id]


def retrieve(question, top_k=3, min_score=0.05):
    q_vec = vectorizer.transform([question])
    scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
    top_indices = scores.argsort()[::-1][:top_k]
    return [(float(scores[i]), FAQ[i]) for i in top_indices if scores[i] >= min_score]


def build_prompt(question, document):
    return f"""당신은 자격증 시험 접수 FAQ 상담원입니다.
아래 근거 안에서만 답하세요. 근거에 없는 내용을 만들지 마세요.
근거로 답할 수 없으면 정확히 UNKNOWN이라고 답하세요.

[질문]
{question}

[근거]
{document.get('reply', document.get('text', ''))}

한국어 두 문장 이내로 답하세요."""


def answer_question(question, generate):
    results = retrieve(question)
    if not results:
        return {"status": "UNKNOWN", "answer": UNKNOWN, "source": "없음", "score": 0}

    best_score, best_doc = results[0]
    generated = generate(build_prompt(question, best_doc)).strip()

    if not generated or generated.upper() == "UNKNOWN":
        return {"status": "UNKNOWN", "answer": UNKNOWN, "source": "없음", "score": best_score}

    return {
        "status": "ANSWERED",
        "answer": generated,
        "source": f"{best_doc.get('cert', '?')} - {best_doc.get('title', '?')}",
        "score": best_score,
    }
