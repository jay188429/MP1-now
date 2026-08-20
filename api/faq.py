import json
import os
import re
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 전역 변수
FAQ = []
vectorizer = None
tfidf_matrix = None
faq_loaded = False
UNKNOWN = "제공된 FAQ에서 확인할 수 없는 내용입니다."

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

def load_faq():
    """JSONL 형식 FAQ 데이터 로드"""
    global FAQ, vectorizer, tfidf_matrix, faq_loaded

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
            vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
            tfidf_matrix = vectorizer.fit_transform(docs)

            faq_loaded = True
            print(f"✓ FAQ 로드 완료: {len(FAQ)}개 항목 (Stage5 - TF-IDF)")
            return True
    except Exception as e:
        print(f"FAQ 로드 오류: {e}")
    return False

def retrieve(question, top_k=3, min_score=0.05):
    """TF-IDF + cosine similarity로 관련 FAQ 검색"""
    if not FAQ or vectorizer is None or tfidf_matrix is None:
        return []

    # 동의어 확장
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
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError('GOOGLE_API_KEY not set')

    model = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

    response = requests.post(url, json={
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }, headers={
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }, timeout=30)

    if response.status_code != 200:
        text = response.text
        raise ValueError(f'Gemini API error: {response.status_code} - {text}')

    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text'].strip()

def build_prompt(question, document):
    """Gemini 프롬프트 생성"""
    reply = document.get('reply', document.get('text', ''))
    return f"""당신은 자격증 시험 접수 FAQ 상담원입니다.
아래 근거 안에서만 답하세요. 근거에 없는 내용을 만들지 마세요.
근거로 답할 수 없으면 정확히 UNKNOWN이라고 답하세요.

[질문]
{question}

[근거]
{reply}

한국어 두 문장 이내로 답하세요."""

def answer_question(question):
    """질문에 대한 답변 생성"""
    results = retrieve(question)

    if not results:
        return {
            "status": "UNKNOWN",
            "answer": UNKNOWN,
            "source": "없음",
            "score": 0
        }

    best_score, best_doc = results[0]

    try:
        generated = call_gemini(build_prompt(question, best_doc))

        if not generated or generated.upper() == "UNKNOWN":
            return {
                "status": "UNKNOWN",
                "answer": UNKNOWN,
                "source": "없음",
                "score": float(best_score)
            }

        return {
            "status": "ANSWERED",
            "answer": generated,
            "source": f"{best_doc.get('cert', '?')} - {best_doc.get('title', '?')}",
            "score": float(best_score)
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "answer": f"오류: {str(e)}",
            "source": "없음",
            "score": float(best_score)
        }

def handler(request):
    """Vercel HTTP handler"""
    # CORS 헤더
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }

    if request.method == 'OPTIONS':
        return ('', 200, headers)

    if request.method != 'POST':
        return json.dumps({'error': 'Method not allowed'}), 405, headers

    try:
        data = request.get_json()
        message = data.get('message', '').strip() if data else ''

        if not message:
            return json.dumps({'error': 'message 필드가 필요합니다'}), 400, headers

        # FAQ 로드 확인
        global faq_loaded
        if not faq_loaded:
            load_faq()

        if not FAQ:
            return json.dumps({'error': 'FAQ 데이터를 로드할 수 없습니다'}), 500, headers

        # 답변 생성
        result = answer_question(message)
        return json.dumps(result), 200, headers

    except Exception as e:
        return json.dumps({'error': str(e)}), 500, headers

# 초기화: 서버 시작 시 FAQ 로드
load_faq()
