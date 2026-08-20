"""
[rag.py] FAQ 검색 + Gemini 프롬프트 생성 - TF-IDF 검색
======================================================
Stage 4의 키워드+토큰 매칭 대신 TF-IDF(Term Frequency - Inverse Document Frequency)를 사용한다.

TF-IDF란:
  - TF (단어 빈도): 해당 문서에서 특정 단어가 얼마나 자주 나오는가
  - IDF (역문서 빈도): 전체 문서에서 특정 단어가 얼마나 희귀한가
  - TF x IDF = 해당 문서에서 중요한 단어일수록 점수가 높다
  - "시험"은 거의 모든 FAQ에 나오므로 IDF가 낮다 (구분력 없음)
  - "굴착기"는 일부 FAQ에만 나오므로 IDF가 높다 (구분력 있음)

scikit-learn의 TfidfVectorizer가 이걸 자동으로 해준다.
cosine_similarity로 질문과 FAQ 사이의 유사도를 계산한다.

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

DOCS = [
    f"{row.get('cert', '')} {row.get('category', '')} {row.get('title', '')} {row.get('body', '')} {row.get('reply', '')}"
    for row in FAQ
]

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(DOCS)


def retrieve(question, top_k=3, min_score=0.05):
    """
    TF-IDF + cosine similarity로 관련 FAQ를 찾는다.
    키워드 매칭과 달리, "굴착기 접수비"를 물어보면
    "굴착기"의 IDF가 높아서 굴착기 관련 FAQ가 정확히 올라온다.
    """
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
