"""
[rag.py] FAQ 검색 + Gemini 프롬프트 생성 - 확장 데이터 (4,705건)
================================================================
Stage 1의 키워드+토큰 매칭을 그대로 사용하지만, 데이터가 40건 -> 4,705건.

한계 체험 포인트:
  - 4,705건에서 키워드 매칭은 정확도가 떨어진다
  - 비슷한 키워드를 가진 다른 자격증 FAQ가 잘못 매칭되는 경우를 관찰하세요
  - "굴착기 접수비"를 물어봤는데 "지게차 접수비"가 나온다면 그게 한계

데이터 포맷 (JSONL):
  {"id": 1, "cert": "요양보호사", "category": "합격기준",
   "title": "요양보호사 합격 기준 문의",
   "body": "요양보호사 합격 기준이 어떻게 되나요?",
   "reply": "필기/실기 각 60% 이상입니다."}

수정 포인트:
  [R1] min_score를 조정해서 검색 결과 변화를 관찰하세요
  [R2] top_k를 늘려서 Gemini에게 여러 근거를 주어보세요
"""
from __future__ import annotations
import json
import re
from pathlib import Path

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


def _tokens(text):
    return set(re.findall(r"[가-힣A-Za-z0-9]+", text.lower()))


def retrieve(question, top_k=3, min_score=2):
    """
    키워드+토큰 매칭으로 관련 FAQ를 찾는다.
    4,705건에서는 비슷한 키워드를 가진 다른 자격증 FAQ가 잘못 올라올 수 있다.
    """
    q = _tokens(question)
    ranked = []
    for row in FAQ:
        cert_match = 3 if row.get("cert", "").lower() in question.lower() else 0
        cat_match = 2 if row.get("category", "").lower() in question.lower() else 0
        text_blob = f"{row.get('title', '')} {row.get('body', '')} {row.get('reply', '')}"
        overlap = len(q & _tokens(text_blob))
        score = cert_match + cat_match + overlap
        ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [(s, r) for s, r in ranked[:top_k] if s >= min_score]


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
