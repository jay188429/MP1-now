"""
[rag.py] FAQ 검색 + Gemini 프롬프트 생성
==========================================
이 파일이 하는 일:
  1. faq.json을 읽어 FAQ 목록을 메모리에 올린다
  2. 사용자 질문이 들어오면 키워드+토큰 매칭으로 가장 관련 높은 FAQ를 찾는다
  3. 찾은 FAQ를 근거로 Gemini 프롬프트를 만든다
  4. Gemini 답변을 받아 결과를 반환한다

검색 흐름:
  질문 "한식 시험비 얼마"
    -> 토큰 분리: {"한식", "시험비", "얼마"}
    -> faq.json 40건 각각과 매칭 점수 계산
    -> 가장 높은 점수의 FAQ를 근거로 선택
    -> Gemini에게 "이 근거 안에서만 답하세요" 프롬프트 전송

수정 포인트:
  [R1] min_score를 낮추면 더 많은 질문에 답한다 (대신 정확도 하락)
  [R2] top_k를 늘리면 여러 근거를 Gemini에게 줄 수 있다
  [R3] build_prompt의 시스템 지시를 수정하면 답변 스타일이 바뀐다
  [R4] faq.json에 FAQ를 추가하면 답변 범위가 넓어진다
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNKNOWN = "제공된 FAQ에서 확인할 수 없는 내용입니다."

# faq.json을 읽어서 FAQ 리스트로 만든다
FAQ = json.loads((ROOT / "faq.json").read_text(encoding="utf-8"))


def _tokens(text):
    """
    텍스트에서 한글/영문/숫자 토큰을 추출한다.
    예: "한식조리 시험비 얼마?" -> {"한식조리", "시험비", "얼마"}
    """
    return set(re.findall(r"[가-힣A-Za-z0-9]+", text.lower()))


def retrieve(question, top_k=3, min_score=2):
    """
    질문과 가장 관련 높은 FAQ를 찾는다.

    점수 계산 방식:
      - keywords 배열의 단어가 질문에 포함되면 +2점씩
      - 질문 토큰과 FAQ 제목+본문 토큰이 겹치면 +1점씩
      - 합산 점수가 min_score 이상인 것만 반환

    question: 사용자 질문 문자열
    top_k:    최대 몇 개까지 반환할지 (기본 3)
    min_score: 이 점수 미만이면 "관련 없음"으로 판단 (기본 2)
    return:   [(점수, FAQ딕셔너리), ...] 높은 순
    """
    q = _tokens(question)
    ranked = []
    for row in FAQ:
        # keywords 매칭: "한식"이 질문에 있으면 +2점
        keyword_hits = sum(2 for key in row["keywords"] if key.lower() in question.lower())
        # 토큰 겹침: 질문 토큰과 FAQ 텍스트 토큰의 교집합 크기
        overlap = len(q & _tokens(row["title"] + " " + row["text"]))
        score = keyword_hits + overlap
        ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    # [R1] min_score 미만은 버린다 - 낮추면 더 많이 답하지만 엉뚱한 답 위험
    results = [(score, row) for score, row in ranked[:top_k] if score >= min_score]
    return results


def build_prompt(question, document):
    """
    Gemini에게 보낼 프롬프트를 만든다.
    핵심: "근거 안에서만 답하세요" - 이게 없으면 Gemini가 지어낸다.

    [R3] 아래 텍스트를 수정하면 답변 스타일이 바뀐다
    예: "존댓말로 답하세요", "세 문장으로 답하세요" 등
    """
    return f"""당신은 자격증 시험 접수 FAQ 상담원입니다.
아래 근거 안에서만 답하세요. 근거에 없는 내용을 만들지 마세요.
근거로 답할 수 없으면 정확히 UNKNOWN이라고 답하세요.

[질문]
{question}

[근거]
{document['text']}

한국어 두 문장 이내로 답하세요."""


def answer_question(question, generate):
    """
    전체 흐름을 실행하는 메인 함수.
    1. retrieve()로 관련 FAQ를 찾는다
    2. 못 찾으면 UNKNOWN 반환 (Gemini 호출 안 함 = API 비용 절약)
    3. 찾으면 build_prompt()로 프롬프트를 만들고 generate()로 Gemini 호출
    4. Gemini가 UNKNOWN이라고 답하면 그대로 반환

    question: 사용자 질문
    generate: gemini.py의 GeminiClient.generate 메서드
    return:   {"status", "answer", "source", "score"} 딕셔너리
    """
    results = retrieve(question)
    if not results:
        # 검색 결과가 없으면 Gemini를 호출하지 않는다
        return {"status": "UNKNOWN", "answer": UNKNOWN, "source": "없음", "score": 0}

    best_score, best_doc = results[0]
    generated = generate(build_prompt(question, best_doc)).strip()

    if not generated or generated.upper() == "UNKNOWN":
        return {"status": "UNKNOWN", "answer": UNKNOWN, "source": "없음", "score": best_score}

    return {
        "status": "ANSWERED",
        "answer": generated,
        "source": f"{best_doc['cert']} - {best_doc['title']}",
        "score": best_score,
    }
