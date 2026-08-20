# MP1 자격증 시험 접수 FAQ 챗봇

## 4축

| 축 | 값 1 | 값 2 |
|---|---|---|
| 데이터 | `40건` faq.json | `4705건` faq_combined.jsonl |
| 검색 | `키워드` 토큰 매칭 | `TF-IDF` scikit-learn cosine_similarity |
| 배포 | `로컬` localhost:7860 | `공유` share=True, xxxxx.gradio.live 72시간 |
| 관리 | `고정` 코드에서만 수정 | `편집` 웹 UI에서 추가/삭제 |

## 단계 요약

| 코드 | 단계명 | 데이터 | 검색 | 배포 | 관리 | 변경 |
|---|---|---|---|---|---|---|
| S1 | 기본형 | 40건 | 키워드 | 로컬 | 고정 | (시작) |
| S2 | 공유 | 40건 | 키워드 | **공유** | 고정 | `S2.배포` app.py 1줄 |
| S3 | 관리 [MUST] | 40건 | 키워드 | 공유 | **편집** | `S3.관리` app.py + rag.py |
| S4 | 확장 | **4705건** | 키워드 | 로컬 | 고정 | `S4.데이터` rag.py |
| S5 | 검색개선 | 4705건 | **TF-IDF** | 로컬 | 고정 | `S5.검색` rag.py + requirements |
| S6 | 완성형 | 4705건 | TF-IDF | **공유** | **편집** | `S6.배포`+`S6.관리` S5+S3 |

**굵은 글씨** = 이 단계에서 변경된 축.

## 공통 준비

1. `.env.example`을 `.env`로 복사
2. `.env`에 Gemini API 키 입력
3. 각 단계의 `requirements.txt` 설치: `pip install -r requirements.txt`


---

## S1 기본형 (stage1_local_basic/)

4축 전부 시작값.

| 축 | 값 | 설명 |
|---|---|---|
| 데이터 | 40건 | faq.json에 8개 자격증 x 5건 |
| 검색 | 키워드 | rag.py `retrieve()`가 토큰 분리 후 keywords 배열과 매칭, 점수 계산 |
| 배포 | 로컬 | app.py 마지막 줄 `demo.launch()`로 localhost:7860 |
| 관리 | 고정 | FAQ를 바꾸려면 faq.json을 직접 편집해야 함 |

실행: `python app.py` -> `http://localhost:7860`


---

## S2 공유 (stage2_share_basic/)

`S2.배포` 로컬 -> 공유. 코드 한 줄만 바뀐다.

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 배포 | 로컬 | **공유** | app.py 마지막 줄 | `demo.launch()` -> `demo.launch(share=True)` |

Gradio가 72시간짜리 공개 URL을 만든다. 나머지 gemini.py, rag.py, faq.json은 S1과 동일.

실행: `python app.py` -> `https://xxxxx.gradio.live`


---

## S3 관리 (stage3_share_admin/) [MUST]

`S3.관리` 고정 -> 편집. S1-S2에서 faq.json 40건은 고정이었다. 이 단계부터 웹에서 수정할 수 있다.

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 관리 | 고정 | **편집** | app.py 전체 | `gr.ChatInterface` -> `gr.Blocks` + `gr.Tab` 2개 (챗봇, FAQ 관리) |
| | | | rag.py 함수 추가 | `reload_faq()` faq.json 다시 읽기 |
| | | | | `add_faq_entry(cert, title, text, keywords)` FAQ 추가 후 저장 |
| | | | | `delete_faq_entry(faq_id)` FAQ 삭제 후 저장 |
| | | | | `get_faq_table()` FAQ 목록을 Dataframe용 리스트로 반환 |

FAQ 관리 탭 구성: Dropdown(자격증) + Textbox(제목, 내용, 키워드) + 추가/삭제 버튼 + Dataframe(목록). 기존 retrieve(), build_prompt()는 S1과 동일.

실행: `python app.py` -> 챗봇 탭 + FAQ 관리 탭

**MUST 챌린지**: FAQ 관리 탭에서 새 FAQ를 추가한 뒤, 챗봇 탭에서 그 내용으로 질문. 방금 넣은 FAQ가 답변에 반영되는지 확인.


---

## S4 확장 (stage4_local_extended/)

`S4.데이터` 40건 -> 4705건. 검색은 키워드 그대로인데 데이터만 바꾼다. 데이터가 커지면 키워드 매칭이 얼마나 부정확해지는지 체험하는 단계.

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 데이터 | 40건 | **4705건** | rag.py 데이터 경로 | `ROOT / "faq.json"` -> `ROOT.parent / "data" / "faq_combined.jsonl"` |
| | | | rag.py 로딩 방식 | JSON 한 번 로드 -> JSONL 줄마다 `json.loads` (`_load_jsonl()` 함수) |
| | | | rag.py 필드 매핑 | `text`, `keywords` -> `body`, `reply`, `category` |
| | | | rag.py 점수 계산 | `cert_match(3점) + cat_match(2점) + overlap`으로 변경 |

app.py, gemini.py는 S1과 동일. 배포는 로컬, 관리는 고정으로 돌아간다.

실행: `python app.py` -> `http://localhost:7860`

**챌린지**: "굴착기 접수비"를 물어봤는데 다른 자격증 답변이 나오면 그게 키워드 매칭의 한계. S5에서 해결한다.


---

## S5 검색개선 (stage5_local_tfidf/)

`S5.검색` 키워드 -> TF-IDF. 데이터는 4705건 그대로인데 검색만 바꾼다. S4에서 틀리던 질문이 맞는다.

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 검색 | 키워드 | **TF-IDF** | rag.py import | `import re` 제거, `from sklearn...import TfidfVectorizer, cosine_similarity` 추가 |
| | | | rag.py 인덱스 구축 | 모듈 수준에서 `TfidfVectorizer().fit_transform()`으로 TF-IDF 행렬 생성 (시작 시 1회) |
| | | | rag.py `retrieve()` | `vectorizer.transform([question])` + `cosine_similarity()` 로 유사도 계산 |
| | | | rag.py 삭제 | `_tokens()`, keyword_hits, overlap 점수 계산 전부 삭제 |
| | | | rag.py min_score | 기본값 2 -> 0.05 (TF-IDF는 0~1 범위) |
| | | | requirements.txt | `scikit-learn` 추가 |

app.py, gemini.py는 S1과 동일.

실행: `python app.py` -> `http://localhost:7860` (`pip install scikit-learn` 필요)

**챌린지**: S4에서 틀렸던 "굴착기 접수비"를 다시 물어본다. TF-IDF는 "굴착기"가 희귀한 단어라 굴착기 FAQ를 정확히 찾는다.


---

## S6 완성형 (stage6_share_full/)

`S6.배포` 로컬 -> 공유 + `S6.관리` 고정 -> 편집. S5에 S3의 관리 기능을 합친 최종 버전.

| 축 | 이전 | 변경 | 파일 | 수정 내용 |
|---|---|---|---|---|
| 배포 | 로컬 | **공유** | app.py 마지막 줄 | `demo.launch(share=True)` |
| 관리 | 고정 | **편집** | app.py 전체 | S3처럼 `gr.Blocks` + `gr.Tab` 2개 (챗봇, FAQ 관리) |
| | | | rag.py CRUD 추가 | S3의 `add_faq_entry()`, `delete_faq_entry()`, `get_faq_table()` |
| | | | rag.py `rebuild_index()` 추가 | FAQ 추가/삭제 후 TF-IDF 행렬을 처음부터 다시 계산 |
| | | | requirements.txt | `scikit-learn` 추가 |

S3에서는 키워드 매칭이라 `reload_faq()`만 하면 됐지만, TF-IDF는 행렬 전체를 다시 만들어야 새 FAQ가 검색에 반영된다. 그래서 `rebuild_index()`가 새로 필요하다.

실행: `python app.py` -> `https://xxxxx.gradio.live` (`pip install scikit-learn` 필요)


---

## 파일별 수정 포인트

| 파일 | 역할 | 수정 포인트 |
|---|---|---|
| app.py | Gradio 챗봇 UI | [A1] 제목 [A2] 예시 질문 |
| gemini.py | Gemini API 호출 | [G1] 모델명 [G2] 타임아웃 |
| rag.py | FAQ 검색 + 프롬프트 | [R1] min_score [R2] top_k [R3] 프롬프트 |
| faq.json | 기본 FAQ 40건 | S1-S3 |
| data/faq_combined.jsonl | 확장 FAQ 4705건 | S4-S6 |
