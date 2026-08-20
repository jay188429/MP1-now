# MP1 FAQ 챗봇 - 단계별 실습 가이드

이 문서는 S1(기본형)에서 S6(완성형)까지 한 축씩 바꿔가며 챗봇을 확장하는 과정을 순서대로 안내한다. 요약은 README.md에 있다. 이 문서는 왜 바꾸는지, 정확히 어디를 고치는지, 어떻게 확인하는지를 다룬다.

## 시작 전 준비

1. Gemini API 키가 필요하다. Google AI Studio(aistudio.google.com)에서 발급한다.
2. 각 단계 폴더 안에 `.env.example`이 있다. 이 파일을 `.env`로 복사한 뒤, 안에 키를 넣는다.
3. `pip install -r requirements.txt`로 패키지를 설치한다. S1-S4는 gradio와 기본 라이브러리만 쓴다. S5부터 scikit-learn이 추가된다.
4. 키를 화면이나 채팅에 붙여넣지 않는다. `.env` 파일 안에만 둔다.

## 4축이 무엇인가

이 프로젝트는 네 가지 축으로 움직인다. 각 단계는 이 중 한두 개만 바꾼다.

| 축 | 의미 | 값 1 | 값 2 |
|---|---|---|---|
| 데이터 | FAQ가 몇 건인가 | 40건 (faq.json) | 4,705건 (faq_combined.jsonl) |
| 검색 | 질문과 FAQ를 어떻게 맞추는가 | 키워드 매칭 | TF-IDF 유사도 |
| 배포 | 어디서 접속하는가 | 로컬 (내 컴퓨터만) | 공유 (72시간 공개 URL) |
| 관리 | FAQ를 어떻게 고치는가 | 고정 (파일 직접 편집) | 편집 (웹에서 추가/삭제) |

단계마다 어떤 축이 바뀌는지 표시한다. 바뀌지 않는 축은 이전 값을 그대로 쓴다.

---

## S1 기본형 (stage1_local_basic/)

### 목적

4축 전부 시작값이다. 챗봇이 작동하는 최소 구조를 확인한다.

### 파일 구조

| 파일 | 역할 |
|---|---|
| app.py | Gradio 화면을 띄운다. 질문을 받아 rag.py에 넘기고 결과를 보여준다. |
| rag.py | faq.json에서 관련 FAQ를 찾고, Gemini에게 보낼 프롬프트를 만든다. |
| gemini.py | Gemini API를 호출한다. urllib로 HTTP 요청을 보낸다. |
| faq.json | FAQ 40건. 8개 자격증 x 5건. |

### 실행 순서

1. 터미널에서 `stage1_local_basic/` 폴더로 이동한다.
2. `.env.example`을 `.env`로 복사한다.
3. `.env`를 열어 `GOOGLE_API_KEY=여기에_키`를 넣는다.
4. `pip install -r requirements.txt`를 실행한다.
5. `python app.py`를 실행한다.
6. 브라우저에서 `http://localhost:7860`이 열린다.
7. "한식조리기능사 시험비가 얼마예요?"를 입력한다.
8. `[ANSWERED]`로 시작하는 답변과 `출처: 한식조리기능사 - ...`가 나오면 성공이다.

### 확인

- 답변에 `[ANSWERED]`가 뜨고, 출처에 자격증 이름이 나온다.
- "내일 날씨 알려줘"처럼 FAQ에 없는 질문을 하면 `[UNKNOWN]`이 나온다.
- 터미널에 에러 없이 실행된다.

### 검색이 작동하는 방식

rag.py의 `retrieve()` 함수가 질문과 FAQ 40건을 비교한다. 비교 방식은 두 가지 점수의 합이다.

- 키워드 점수: faq.json의 keywords 배열에 있는 단어가 질문에 포함되면 단어당 +2점.
- 토큰 겹침 점수: 질문을 단어 단위로 쪼갠 것과 FAQ 텍스트를 단어 단위로 쪼갠 것의 겹치는 개수. 겹칠 때마다 +1점.

합산 점수가 2점(min_score) 이상인 FAQ만 후보가 된다. 후보 중 점수가 가장 높은 것을 Gemini에게 넘긴다.

### 주의

- `.env` 파일 이름 앞에 점(.)이 있다. 파일 탐색기에서 안 보일 수 있다. 터미널에서 `ls -a`로 확인한다.
- `python app.py` 실행 후 "Address already in use" 에러가 나면, 이전에 실행한 챗봇이 아직 떠 있는 것이다. 이전 터미널에서 Ctrl+C로 먼저 끈다.
- gemini.py는 수정할 일이 거의 없다. 모델명(`gemini-2.5-flash-lite`)과 타임아웃만 건드릴 수 있다.

---

## S2 공유 (stage2_share_basic/)

### 목적

`배포` 축을 로컬에서 공유로 바꾼다. 코드 한 줄만 바뀐다.

### 바뀌는 것

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 배포 | 로컬 | 공유 | app.py 마지막 줄 | `demo.launch()` -> `demo.launch(share=True)` |

### 수정 순서

1. `stage2_share_basic/`에서 `.env`를 준비한다 (S1과 같은 키).
2. app.py를 연다.
3. 마지막 줄 `demo.launch()`에 `share=True`를 넣는다: `demo.launch(share=True)`.
4. `python app.py`를 실행한다.
5. 터미널에 `Running on public URL: https://xxxxx.gradio.live`가 뜬다.
6. 이 URL을 브라우저에 붙여넣는다. 다른 기기(휴대폰 등)에서도 열 수 있다.

### 확인

- 터미널에 `https://xxxxx.gradio.live` 형태의 URL이 표시된다.
- 그 URL에서 챗봇이 작동한다.
- 이 URL은 72시간 동안 유효하다. 72시간이 지나면 새로 실행해야 한다.

### 왜 이렇게 하는가

Gradio의 `share=True`는 Gradio 서버가 터널을 만들어 외부에서 접속할 수 있게 한다. 내 컴퓨터가 서버 역할을 하되, Gradio가 중간에서 URL을 연결해 준다. 별도 서버(Vercel 등)에 올리는 것이 아니라 내 컴퓨터에서 실행 중인 프로그램에 외부 URL을 붙이는 것이다.

한 줄 바꾼 것뿐인데 다른 사람에게 보여줄 수 있게 됐다. 나머지 파일은 S1과 완전히 같다.

### 주의

- 공유 URL이 생성되는 데 10-30초 걸릴 수 있다. "Could not create share link"가 뜨면 방화벽이나 네트워크 환경 문제다. 그 경우 S1처럼 로컬로만 확인한다.
- 공유 URL이 열려 있는 동안 터미널을 닫으면 안 된다. 터미널이 닫히면 URL도 끊긴다.
- 공유 URL은 누구나 접속할 수 있다. API 키가 서버 쪽(.env)에만 있으므로 접속자에게 노출되지 않는다.

---

## S3 관리 (stage3_share_admin/) [MUST]

### 목적

`관리` 축을 고정에서 편집으로 바꾼다. 지금까지 FAQ를 바꾸려면 faq.json 파일을 직접 열어야 했다. 이 단계부터 웹 화면에서 FAQ를 추가하고 삭제할 수 있다.

이 단계는 MUST 챌린지다. S2까지는 따라하기인데, S3부터는 직접 해결해야 하는 과제가 포함된다.

### 바뀌는 것

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 관리 | 고정 | 편집 | app.py 전체 | ChatInterface 1개 -> Blocks 안에 Tab 2개 |
| | | | rag.py 함수 4개 추가 | reload_faq, add_faq_entry, delete_faq_entry, get_faq_table |

### 수정 순서

app.py를 크게 바꾸는 단계다. S1-S2의 app.py는 `gr.ChatInterface` 한 줄로 화면을 만들었다. S3는 `gr.Blocks`로 화면 구조를 직접 짠다.

**app.py 변경:**

1. import에 rag.py의 새 함수 4개를 추가한다: `reload_faq, get_faq_table, add_faq_entry, delete_faq_entry`.
2. `gr.ChatInterface(...)` 한 줄을 지우고, `with gr.Blocks(...) as demo:` 블록으로 교체한다.
3. 블록 안에 Tab 2개를 만든다:
   - `with gr.Tab("챗봇"):` - 기존 채팅 기능. ChatInterface를 이 탭 안에 넣는다.
   - `with gr.Tab("FAQ 관리"):` - 추가/삭제 폼과 목록 테이블.
4. FAQ 관리 탭 안에 넣을 것:
   - Dropdown(자격증 선택), Textbox(제목), Textbox(내용), Textbox(키워드) - 입력 폼.
   - Button("FAQ 추가") - 누르면 `add_faq_entry()`를 호출하고 `reload_faq()`로 갱신.
   - Textbox(삭제할 ID) + Button("삭제") - 누르면 `delete_faq_entry()` 호출.
   - Dataframe - `get_faq_table()`의 결과를 표시. 현재 FAQ 목록을 보여준다.
5. 마지막 줄: `demo.launch(share=True)`.

**rag.py 변경:**

6. 파일 경로를 변수로 분리한다: `FAQ_PATH = ROOT / "faq.json"`.
7. `reload_faq()` 함수 추가: faq.json을 다시 읽어 메모리에 올린다. FAQ를 추가/삭제한 뒤 이 함수를 불러야 챗봇이 새 데이터로 답한다.
8. `_save_faq()` 함수 추가: 메모리의 FAQ 리스트를 faq.json에 다시 쓴다.
9. `get_faq_table()` 함수 추가: FAQ 전체를 `[[id, cert, title, keywords], ...]` 형태로 반환한다. Gradio Dataframe에 넣을 형태다.
10. `add_faq_entry(cert, title, text, keywords)` 함수 추가: 새 FAQ를 만들어 리스트에 넣고 `_save_faq()`로 저장한다. ID는 `CUSTOM_N` 형태로 자동 생성된다.
11. `delete_faq_entry(faq_id)` 함수 추가: 해당 ID의 FAQ를 리스트에서 제거하고 `_save_faq()`로 저장한다.

기존 `retrieve()`, `build_prompt()`, `answer_question()`은 바꾸지 않는다.

### 확인

- `python app.py` 실행 후 화면에 탭 2개(챗봇, FAQ 관리)가 보인다.
- 챗봇 탭에서 질문하면 S1과 같은 답변이 나온다.
- FAQ 관리 탭에서 "한식조리기능사 / 신규 테스트 / 테스트 답변입니다 / 테스트,신규"를 입력하고 추가 버튼을 누른다.
- 챗봇 탭으로 돌아가 "신규 테스트"를 질문한다.
- 방금 추가한 FAQ가 답변에 반영되면 MUST 완료.

### MUST 챌린지 (직접 해결)

FAQ 관리 탭에서 본인이 정한 자격증에 새 FAQ를 하나 추가한 뒤, 챗봇 탭에서 그 내용으로 질문한다. 추가한 FAQ가 답변의 출처로 나타나야 한다.

- 추가하기 전에 같은 질문을 먼저 해 본다. `[UNKNOWN]`이 나오거나 다른 FAQ가 출처로 잡힐 것이다.
- 추가한 뒤 같은 질문을 다시 한다. 이번에는 내가 넣은 FAQ가 출처로 잡혀야 한다.
- 이 "전/후 비교"가 핵심이다. 데이터가 바뀌면 답변이 바뀐다는 것을 직접 확인하는 것이다.

### 왜 이렇게 하는가

`gr.ChatInterface`는 채팅 화면 하나를 빠르게 만들 때 쓴다. 화면이 한 종류밖에 안 된다. `gr.Blocks`는 화면 구조를 자유롭게 짤 수 있다. Tab, Row, Column으로 여러 화면을 하나의 앱 안에 넣을 수 있다.

FAQ를 파일에서만 고칠 수 있는 챗봇은 관리자가 아닌 사람이 쓸 수 없다. 웹 화면에서 고칠 수 있어야 비개발자도 FAQ를 관리할 수 있다. 이것이 "고정에서 편집으로" 바꾸는 이유다.

### 주의

- `reload_faq()`를 빠뜨리면 FAQ를 추가해도 챗봇이 이전 데이터로 답한다. 추가/삭제 후 반드시 `reload_faq()`를 호출한다.
- `_save_faq()` 없이 메모리만 바꾸면, `python app.py`를 다시 실행했을 때 추가한 FAQ가 사라진다. 반드시 파일에 저장해야 한다.
- Gradio Blocks에서 `btn.click(fn, inputs, outputs)` 구문을 써야 버튼이 작동한다. `with` 블록 안에 버튼을 배치한 것만으로는 동작하지 않는다.
- `gr.ChatInterface`를 Tab 안에 넣을 때, Tab 밖에 두면 탭 구조가 깨진다.

---

## S4 확장 (stage4_local_extended/)

### 목적

`데이터` 축을 40건에서 4,705건으로 바꾼다. 검색 방식(키워드 매칭)은 그대로 둔다. 데이터가 커지면 키워드 매칭이 얼마나 부정확해지는지 체험하는 단계다.

### 바뀌는 것

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 데이터 | 40건 | 4,705건 | rag.py 데이터 경로 | faq.json -> data/faq_combined.jsonl |
| | | | rag.py 로딩 방식 | JSON 한 번 읽기 -> JSONL 줄마다 파싱 |
| | | | rag.py 필드 이름 | text, keywords -> body, reply, category |
| | | | rag.py 점수 계산 | keyword_hits -> cert_match + cat_match |

배포는 로컬로, 관리는 고정으로 돌아간다. S3의 편집 기능은 여기서 빠진다(S6에서 다시 합친다).

### 수정 순서

이 단계는 rag.py만 바뀐다. app.py와 gemini.py는 S1과 같다.

**rag.py 변경:**

1. 데이터 경로를 바꾼다. `ROOT / "faq.json"` 대신 `ROOT.parent / "data" / "faq_combined.jsonl"`을 가리킨다. 이 파일은 `mp1-chatbot/data/` 폴더에 이미 있다.
2. `_load_jsonl(path)` 함수를 추가한다. JSONL은 한 줄에 JSON 한 건이 들어 있는 형식이다. 줄마다 `json.loads()`로 파싱한다.
3. `FAQ = json.loads(...)` 대신 `FAQ = _load_jsonl(DATA_PATH)`로 교체한다.
4. `retrieve()` 함수의 점수 계산을 바꾼다:
   - 기존: `keyword_hits`(keywords 배열 매칭, 단어당 +2)
   - 변경: `cert_match`(자격증명이 질문에 포함되면 +3) + `cat_match`(카테고리가 질문에 포함되면 +2) + `overlap`(토큰 겹침)
5. 필드 접근을 바꾼다: 기존 `row["text"]`, `row["keywords"]` 대신 `row.get("body")`, `row.get("reply")`, `row.get("category")`를 쓴다.

### 확인

- "한식조리기능사 시험비가 얼마예요?"에 여전히 답한다.
- "요양보호사 합격 기준"에 답한다.
- "굴착기 접수비"를 물어본다. 이때 답변 출처가 굴착기가 아니라 다른 자격증(예: 지게차)이 나올 수 있다. 이것이 키워드 매칭의 한계다. S5에서 해결한다.

### 왜 이렇게 하는가

**JSON vs JSONL**: faq.json은 파일 전체가 하나의 JSON 배열이다. 40건일 때는 문제없지만, 4,705건이 되면 파일 하나가 크다. JSONL은 줄 하나가 독립된 JSON이라 한 줄씩 읽을 수 있고, 새 데이터를 줄 끝에 붙이기 쉽다.

**필드가 다른 이유**: faq.json(40건)은 학습용으로 만든 샘플이라 `text`, `keywords` 같은 간단한 필드명을 썼다. faq_combined.jsonl(4,705건)은 실제 Q&A 게시판과 전화 상담 데이터를 합친 것이라 `body`(질문 본문), `reply`(답변), `category`(분류) 같은 필드명을 쓴다.

**키워드 매칭의 한계**: 40건에서는 "굴착기"가 들어간 FAQ가 몇 개 없어서 잘 찾았다. 4,705건에서는 "접수비"라는 단어가 여러 자격증 FAQ에 공통으로 들어 있어서, "굴착기"보다 "접수비"의 겹침 점수가 높은 다른 자격증 FAQ가 올라온다. 이 문제를 해결하려면 검색 방식 자체를 바꿔야 한다.

### 주의

- data/faq_combined.jsonl 파일이 `mp1-chatbot/data/` 폴더에 있어야 한다. stage4 폴더 안이 아니다. 경로가 `ROOT.parent / "data" / ...`이므로 한 단계 위(mp1-chatbot/)에서 data 폴더를 찾는다.
- 이 단계에서 S3의 관리 기능(추가/삭제)은 빠져 있다. S4는 "데이터 규모만 바꿨을 때 무슨 일이 일어나는지" 관찰하는 단계다.
- `_load_jsonl()`에서 빈 줄을 건너뛰는 `if line:` 조건이 있다. JSONL 파일 끝에 빈 줄이 있으면 `json.loads("")`가 에러를 낸다.

---

## S5 검색개선 (stage5_local_tfidf/)

### 목적

`검색` 축을 키워드 매칭에서 TF-IDF로 바꾼다. 데이터는 4,705건 그대로다. S4에서 틀리던 질문이 맞는다.

### 바뀌는 것

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 검색 | 키워드 | TF-IDF | rag.py import | re 제거, sklearn의 TfidfVectorizer와 cosine_similarity 추가 |
| | | | rag.py 인덱스 구축 | 모듈 로드 시 TF-IDF 행렬을 한 번 만든다 |
| | | | rag.py retrieve() | cosine_similarity로 유사도 계산 |
| | | | rag.py 삭제 | _tokens(), keyword_hits, overlap 전부 삭제 |
| | | | rag.py min_score | 2 -> 0.05 (TF-IDF는 0~1 범위) |
| | | | requirements.txt | scikit-learn 추가 |

### 수정 순서

**패키지 설치:**

1. `pip install scikit-learn`을 실행한다. 또는 `pip install -r requirements.txt` (이 단계의 requirements.txt에 scikit-learn이 포함돼 있다).

**rag.py 변경:**

2. `import re`를 지운다. 더 이상 `_tokens()` 함수를 쓰지 않으므로 re가 필요 없다.
3. `from sklearn.feature_extraction.text import TfidfVectorizer`를 추가한다.
4. `from sklearn.metrics.pairwise import cosine_similarity`를 추가한다.
5. FAQ 로딩 직후에 DOCS 리스트를 만든다. 각 FAQ의 모든 텍스트 필드(cert, category, title, body, reply)를 하나의 문자열로 합친다.
6. `vectorizer = TfidfVectorizer()`로 벡터라이저를 만든다.
7. `tfidf_matrix = vectorizer.fit_transform(DOCS)`로 TF-IDF 행렬을 만든다. 이 줄이 실행될 때 4,705건 전체를 분석해서 각 단어의 중요도를 계산한다.
8. `_tokens()` 함수를 삭제한다.
9. `retrieve()` 함수를 교체한다:
   - `q_vec = vectorizer.transform([question])` - 질문도 같은 벡터 공간으로 변환.
   - `scores = cosine_similarity(q_vec, tfidf_matrix).flatten()` - 질문과 4,705건 각각의 유사도를 계산.
   - `top_indices = scores.argsort()[::-1][:top_k]` - 유사도 높은 순으로 정렬.
   - min_score를 0.05로 바꾼다 (TF-IDF 유사도는 0에서 1 사이 값이다).

### 확인

- "한식조리기능사 시험비가 얼마예요?"에 답한다.
- "굴착기 접수비"를 물어본다. 이번에는 출처가 굴착기 관련 FAQ다. S4에서 틀리던 것이 맞는다.
- "요양보호사 실기 준비물"을 물어본다.
- 답변 결과에 유사도 점수가 보인다(0에서 1 사이 소수).

### TF-IDF가 무엇인가

TF-IDF는 "이 문서에서 이 단어가 얼마나 중요한가"를 숫자로 매기는 방법이다.

- TF(Term Frequency): 해당 문서에서 특정 단어가 몇 번 나오는가. 많이 나올수록 높다.
- IDF(Inverse Document Frequency): 전체 문서에서 특정 단어가 얼마나 드문가. 드물수록 높다.
- TF x IDF = 이 문서에서 자주 나오면서 다른 문서에는 드문 단어일수록 점수가 높다.

예를 들어 "시험"이라는 단어는 4,705건 FAQ 거의 전부에 나온다. IDF가 낮다. 어떤 FAQ를 골라야 할지 구분하는 힘이 없다. "굴착기"라는 단어는 굴착기 관련 FAQ에만 나온다. IDF가 높다. "굴착기 접수비"를 물어보면 "굴착기"의 높은 IDF 덕에 굴착기 FAQ가 정확히 올라온다.

키워드 매칭은 단어가 있는지 없는지만 본다. TF-IDF는 그 단어가 얼마나 희귀한지도 본다. 그래서 4,705건처럼 데이터가 많아도 정확하다.

### 왜 이렇게 하는가

S4에서 체험한 것처럼, 키워드 매칭은 데이터가 적을 때(40건)는 잘 작동하지만 데이터가 많아지면(4,705건) 정확도가 떨어진다. 같은 키워드("접수비", "시험")가 여러 자격증에 걸쳐 나오기 때문이다.

TF-IDF는 이 문제를 "단어의 희귀성"으로 해결한다. scikit-learn 라이브러리가 계산을 전부 해 준다. 직접 수학을 구현할 필요는 없다.

### 주의

- `scikit-learn`을 설치하지 않으면 `ModuleNotFoundError: No module named 'sklearn'`이 뜬다.
- TF-IDF 행렬은 프로그램 시작 시 한 번 만든다. 4,705건을 분석하므로 시작에 1-2초 걸릴 수 있다. 정상이다.
- `min_score=0.05`는 TF-IDF 유사도 기준이다. 키워드 매칭의 `min_score=2`와 단위가 다르다. TF-IDF 유사도는 0(전혀 관련 없음)에서 1(완전히 같음) 사이 값이다.
- 이 단계에서 FAQ 관리 기능(추가/삭제)은 없다. S4처럼 로컬, 고정이다.

---

## S6 완성형 (stage6_share_full/)

### 목적

`배포`를 공유로, `관리`를 편집으로 바꾼다. S5의 TF-IDF 검색에 S3의 FAQ 관리를 합친 최종 버전이다. 4축 전부 값 2가 된다.

### 바뀌는 것

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 배포 | 로컬 | 공유 | app.py 마지막 줄 | `demo.launch(share=True)` |
| 관리 | 고정 | 편집 | app.py 전체 | Blocks + Tab 2개 (S3과 같은 구조) |
| | | | rag.py CRUD 추가 | add_faq_entry, delete_faq_entry, get_faq_table |
| | | | rag.py rebuild_index() | FAQ 변경 후 TF-IDF 행렬 재구축 |

### 수정 순서

S3의 관리 기능과 S5의 TF-IDF 검색을 합치는 단계다. 새로 만드는 것보다 "두 코드를 합치는" 작업이다.

**app.py 변경 (S3 기반 + S5 결과 표시):**

1. S3처럼 `gr.Blocks` + `gr.Tab` 2개로 화면을 구성한다.
2. 챗봇 탭의 답변 포맷에 유사도 점수를 추가한다: `(유사도: {result['score']:.2f})`.
3. FAQ 관리 탭의 입력 필드를 JSONL 형식에 맞춘다: `cert, category, title, reply` (S3은 `cert, title, text, keywords`였다).
4. 추가/삭제 후 `reload_faq()` 대신 `rebuild_index()`를 호출한다.
5. 마지막 줄: `demo.launch(share=True)`.

**rag.py 변경 (S5 기반 + S3 CRUD 합치기):**

6. S5의 TF-IDF 검색 코드를 그대로 가져온다 (TfidfVectorizer, cosine_similarity, retrieve).
7. S3의 CRUD 함수들을 가져오되, 필드를 JSONL 형식에 맞춘다:
   - `add_faq_entry(cert, category, title, reply)` - S3은 `(cert, title, text, keywords)`였다.
   - `delete_faq_entry(faq_id)` - ID가 문자열(CUSTOM_N)이 아니라 숫자다.
8. `_build_docs(faq_list)` 헬퍼 함수를 추가한다. FAQ 리스트를 DOCS 문자열 리스트로 변환한다.
9. `rebuild_index()` 함수를 추가한다:
   - `global vectorizer, tfidf_matrix` 선언.
   - `vectorizer = TfidfVectorizer()` 새로 만들기.
   - `tfidf_matrix = vectorizer.fit_transform(_build_docs(FAQ))` 전체 재계산.
10. S3에서는 `reload_faq()`로 충분했지만, S6에서는 `rebuild_index()`가 필요하다. TF-IDF는 행렬 전체를 다시 만들어야 새 FAQ가 검색에 반영된다.

### 확인

- 공유 URL이 생성된다.
- 챗봇 탭에서 "굴착기 접수비"를 물어보면 정확한 답이 나오고 유사도 점수가 표시된다.
- FAQ 관리 탭에서 새 FAQ를 추가한다.
- 추가 결과 메시지에 "TF-IDF 재구축됨"이 표시된다.
- 챗봇 탭에서 추가한 FAQ 내용으로 질문한다. 반영되면 완성.

### S3의 reload_faq()와 S6의 rebuild_index()는 무엇이 다른가

S3(키워드 매칭)에서는 FAQ를 추가한 뒤 `reload_faq()`만 호출하면 됐다. 키워드 매칭은 질문이 올 때마다 전체 FAQ를 처음부터 비교하기 때문에, 메모리에 새 FAQ가 올라오면 바로 검색 대상에 포함된다.

S6(TF-IDF)에서는 다르다. TF-IDF는 프로그램 시작 시 전체 FAQ로 행렬을 한 번 만들어 둔다. 새 FAQ를 메모리에 올리는 것만으로는 이 행렬에 반영되지 않는다. `rebuild_index()`가 행렬을 처음부터 다시 만든다. 이 함수가 없으면 FAQ를 추가해도 검색에 잡히지 않는다.

비유하면 이렇다. 키워드 매칭은 서류더미를 매번 처음부터 한 장씩 뒤지는 것이다. 서류를 한 장 넣으면 다음에 뒤질 때 자동으로 포함된다. TF-IDF는 서류 전체의 색인 목록을 미리 만들어 두는 것이다. 서류를 한 장 넣은 뒤 색인 목록을 다시 만들어야 그 서류가 검색에 잡힌다.

### 주의

- `rebuild_index()`를 빠뜨리면 FAQ를 추가해도 검색에 반영되지 않는다. 이것이 S3과 S6의 가장 큰 차이다.
- `rebuild_index()`는 4,705건 전체를 다시 계산하므로 추가/삭제마다 1-2초 걸린다. 정상이다.
- S6의 `delete_faq_entry()`는 ID가 숫자(int)다. S3의 ID는 문자열("CERT_001" 같은 형태)이었다. JSONL 데이터의 ID가 숫자이기 때문이다.
- `get_faq_table()`에 검색 기능이 추가됐다. 4,705건 전체를 보여주면 화면이 넘치므로, 자격증명이나 카테고리로 필터링하고 최근 50건만 보여준다.

---

## 단계 사이 관계 정리

```
S1 기본형 (40건, 키워드, 로컬, 고정)
 |
 +-- S2: 배포만 바꿈 (로컬 -> 공유, 1줄)
 |
 +-- S3: 관리만 바꿈 (고정 -> 편집, app.py 재작성 + rag.py 함수 4개)  [MUST]
 |
 +-- S4: 데이터만 바꿈 (40건 -> 4705건, rag.py 경로/필드/점수)
      |
      +-- S5: 검색만 바꿈 (키워드 -> TF-IDF, rag.py 전면 교체)
           |
           +-- S6: S5 + S3 합침 (배포+관리 바꿈, rebuild_index 추가)
```

S2와 S3은 S1에서 독립적으로 갈라진다(한 축만 바꾼다). S4는 S1 기반이지만 데이터만 바꾼다. S5는 S4 위에 검색을 바꾼다. S6는 S5 위에 S3의 관리 기능을 합친다.

이 구조 덕에 "한 번에 하나만 바꿨을 때 무슨 일이 일어나는지"를 관찰할 수 있다. 한꺼번에 바꾸면 뭐 때문에 결과가 달라졌는지 알 수 없다.

---

## 수정할 수 있는 곳 (수정 포인트)

모든 단계에서 아래 값들을 바꿔볼 수 있다. 바꾼 뒤 결과가 어떻게 달라지는지 관찰하는 것이 목적이다.

| 코드 | 파일 | 위치 | 바꾸면 달라지는 것 |
|---|---|---|---|
| [A1] | app.py | title, description | 챗봇 제목과 설명 |
| [A2] | app.py | EXAMPLES 리스트 | 화면에 보이는 예시 질문 |
| [G1] | gemini.py | model 파라미터 | Gemini 모델 종류. 기본값 gemini-2.5-flash-lite |
| [G2] | gemini.py | timeout | API 응답 대기 시간(초) |
| [R1] | rag.py | min_score | 검색 문턱. 낮추면 더 많이 답하지만 정확도가 떨어진다 |
| [R2] | rag.py | top_k | Gemini에게 넘기는 근거 개수. 늘리면 답변이 풍부해지지만 프롬프트가 길어진다 |
| [R3] | rag.py | build_prompt() | 시스템 프롬프트. 답변 스타일을 바꿀 수 있다 |

---

## 이 챗봇의 알려진 한계 (MP1 범위 밖)

MP1에서는 다루지 않지만 알아두면 좋은 한계가 있다.

**대화 맥락을 기억하지 못한다.** 매 질문을 독립적으로 처리한다. "한식조리 접수비 얼마예요?"라고 물은 뒤 "그럼 실기는?"이라고 이어 물으면, 챗봇은 "그럼"이 한식조리를 가리킨다는 걸 모른다. 직전 대화를 검색에 넘기지 않기 때문이다.

이 한계 때문에 생기는 현상:
- 후속 질문("그건 몇 점이에요?")에 엉뚱한 답이 나온다
- "아까 물어본 거 다시 알려줘"가 작동하지 않는다
- 자격증 종류를 매번 명시해야 한다

이것은 구현 결함이 아니라 설계상의 범위 결정이다. 대화 맥락 유지는 별도 주제이고, MP1의 목적(FAQ 검색 방식 비교)과는 다른 문제다.
