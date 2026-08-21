// Stage5: TF-IDF 기반 검색 (Node.js 구현)

let FAQ = [];
let faqLoaded = false;
let docTermFreq = []; // 각 문서의 단어 빈도

const SYNONYMS_DICT = {
  "포크레인": "굴착기",
  "포클레인": "굴착기",
  "요보사": "요양보호사",
  "한조기": "한식조리기능사",
  "개사": "공인중개사",
  "공개사": "공인중개사",
  "손평사": "손해평가사",
  "지게차면허": "지게차운전기능사",
  "전기기사": "전기기능사"
};

function expandSynonyms(text) {
  let expanded = text;
  for (const [short, full] of Object.entries(SYNONYMS_DICT)) {
    const regex = new RegExp(short, 'gi');
    expanded = expanded.replace(regex, full);
  }
  return expanded;
}

// 한글 + 영숫자 토큰화
function tokenize(text) {
  return (text.match(/[가-힣a-zA-Z0-9]+/g) || []).map(t => t.toLowerCase());
}

// TF (Term Frequency) 계산
function computeTF(tokens) {
  const tf = {};
  const totalTerms = tokens.length;
  for (const token of tokens) {
    tf[token] = (tf[token] || 0) + 1;
  }
  // 정규화
  for (const token in tf) {
    tf[token] = tf[token] / totalTerms;
  }
  return tf;
}

// IDF (Inverse Document Frequency) 계산
function computeIDF(allDocs) {
  const docFreq = {};
  const totalDocs = allDocs.length;

  for (const tokens of allDocs) {
    const uniqueTokens = new Set(tokens);
    for (const token of uniqueTokens) {
      docFreq[token] = (docFreq[token] || 0) + 1;
    }
  }

  const idf = {};
  for (const token in docFreq) {
    idf[token] = Math.log((totalDocs + 1) / (docFreq[token] + 1));
  }
  return idf;
}

// 두 벡터 간 코사인 유사도
function cosineSimilarity(vecA, vecB) {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (const token in vecA) {
    if (vecB[token]) {
      dotProduct += vecA[token] * vecB[token];
    }
    normA += vecA[token] * vecA[token];
  }
  for (const token in vecB) {
    normB += vecB[token] * vecB[token];
  }

  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);

  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (normA * normB);
}

function retrieve(question, topK = 3, minScore = 0.01) {
  if (!FAQ.length || !docTermFreq.length) return [];

  const expandedQuestion = expandSynonyms(question);
  const questionTokens = tokenize(expandedQuestion);
  const questionTF = computeTF(questionTokens);

  // IDF 로드 (미리 계산된 것)
  const idf = computeIDF(docTermFreq.map(df => Object.keys(df)));

  // TF-IDF 벡터 계산
  const questionTFIDF = {};
  for (const token in questionTF) {
    questionTFIDF[token] = questionTF[token] * (idf[token] || 0);
  }

  const scores = [];
  for (let i = 0; i < FAQ.length; i++) {
    const docTFIDF = {};
    for (const token in docTermFreq[i]) {
      docTFIDF[token] = docTermFreq[i][token] * (idf[token] || 0);
    }
    const similarity = cosineSimilarity(questionTFIDF, docTFIDF);
    scores.push([similarity, FAQ[i]]);
  }

  scores.sort((a, b) => b[0] - a[0]);
  return scores.slice(0, topK).filter(item => item[0] >= minScore);
}

async function answerQuestion(question) {
  const results = retrieve(question);

  if (results.length === 0) {
    return {
      status: 'UNKNOWN',
      answer: '제공된 FAQ에서 확인할 수 없는 내용입니다.',
      source: '없음',
      score: 0
    };
  }

  const [bestScore, bestDoc] = results[0];
  const title = bestDoc.title || '?';
  const cert = bestDoc.cert || '?';
  const fallbackReply = bestDoc.reply || bestDoc.text || '내용을 확인할 수 없습니다.';

  // Gemini API 호출 완전 제거 (429 에러 원천 차단)
  return {
    status: 'FALLBACK_ANSWERED',
    answer: `${fallbackReply}`,
    source: `${cert} - ${title} (유사도: ${(bestScore).toFixed(2)})`,
    score: bestScore
  };
}

async function loadFAQ() {
  try {
    const response = await fetch('https://mp1-now.vercel.app/faq_combined.jsonl');
    if (response.ok) {
      const text = await response.text();
      FAQ = text
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .map(line => JSON.parse(line));

      // TF 미리 계산
      docTermFreq = FAQ.map(doc => {
        const textBlob = `${doc.cert || ''} ${doc.category || ''} ${doc.title || ''} ${doc.body || ''} ${doc.reply || ''}`;
        const tokens = tokenize(textBlob);
        return computeTF(tokens);
      });

      faqLoaded = true;
      console.log(`✓ FAQ 로드 완료: ${FAQ.length}개 항목 (Stage5 - TF-IDF)`);
    } else {
      console.error(`FAQ 로드 실패: ${response.status}`);
    }
  } catch (error) {
    console.error('FAQ 로드 오류:', error.message);
  }
}

// 핸들러 실행 시 FAQ 로드
const faqPromise = loadFAQ();

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { message } = req.body;

  if (!message) {
    return res.status(400).json({ error: 'message 필드가 필요합니다' });
  }

  try {
    // FAQ가 아직 로드되지 않았으면 기다리기
    if (!faqLoaded) {
      await faqPromise;
    }

    // FAQ가 여전히 로드되지 않았으면 재시도
    if (!faqLoaded || FAQ.length === 0) {
      await loadFAQ();
    }

    const result = await answerQuestion(message);
    return res.status(200).json(result);
  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
