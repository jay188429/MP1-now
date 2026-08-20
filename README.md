# MP1-now: 자격증 FAQ 챗봇 시스템

TF-IDF 기반 검색과 Gemini API를 활용한 지능형 자격증 시험 접수 FAQ 챗봇입니다.

## 📊 시스템 구성

### Stage 3 → 4 → 5 → 6 진화

| Stage | 항목 수 | 검색 방식 | 주요 기능 |
|-------|--------|---------|---------|
| 3 | 40개 | 키워드+토큰 | 기본 매칭 |
| 4 | 4,705개 | 키워드+토큰+동의어 | 동의어 확장 |
| 5 | 4,705개 | TF-IDF | 정확한 유사도 |
| **6** | **4,705개** | **TF-IDF** | **Gradio 관리자 UI** |

## 🚀 배포 방식

### 1️⃣ Vercel (프로덕션)
- 메인 페이지: https://mp1-now.vercel.app
- FAQ 챗봇: https://mp1-now.vercel.app/faq
- API: https://mp1-now.vercel.app/api/faq
- 관리자: https://mp1-now.vercel.app/admin.html

### 2️⃣ Hugging Face Spaces (Stage 6 Gradio)
- 챗봇 탭 (TF-IDF 검색)
- FAQ 관리 탭 (추가/삭제/검색)
- 자동 TF-IDF 재구축

### 3️⃣ 웹 UI 포팅 (Vercel 통합)
- Gradio → HTML/JavaScript 변환
- 현재 아키텍처 통합

## 🔧 기술 스택

- **프론트엔드**: HTML5, JavaScript, CSS3
- **백엔드**: Node.js (Vercel Functions)
- **AI**: Gemini 3.5-flash API
- **검색**: TF-IDF + Cosine Similarity
- **데이터**: 4,705개 JSONL 형식

## 📄 라이선스

MIT

---

**최종 버전**: Stage 6 (2026-08-20)
