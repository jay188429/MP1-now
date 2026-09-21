// Stage7: TF-IDF 검색 + 자격증 종목 필터 (Node.js 구현)
//
// Stage5 대비 변경점
//  1) 질의에서 자격증 종목을 식별해 해당 종목 문서로 후보를 좁힌다.
//     - 기존에는 "공인중개사 접수 기간"에 굴착기 문서가 1등으로 올라왔다.
//  2) 종목이 식별되지 않으면 답을 만들지 않고 어느 자격증인지 되묻는다.
//     - 문서가 모두 종목에 묶여 있으므로, 종목을 모르면 원리상 답할 수 없다.
//  3) 유사도 임계값을 0.01에서 올린다. 0.01은 사실상 모든 문서를 통과시켰다.
//  4) 전화 상담 녹취(3,502건)를 실제로 답변에 사용한다.
//     - 데이터 4,705건 중 3,502건은 reply 없이 opening + exchanges[{caller, staff}] 구조였다.
//       기존 코드는 이 구조를 읽지 못해 검색에는 걸려도 "내용을 확인할 수 없습니다"만 반환했다.
//       즉 실제 답변 가능한 문서는 1,203건(25.6%)뿐이었다.
//  5) IDF와 문서 벡터를 로드 시 1회만 계산한다. (기존에는 매 질의마다 재계산)

let FAQ = [];
let faqLoaded = false;
let docTermFreq = [];  // 각 문서의 단어 빈도
let IDF = {};          // 선계산된 IDF
let docVectors = [];   // 선계산된 문서 TF-IDF 벡터
let docNorms = [];     // 선계산된 문서 벡터 크기

// 유사도 임계값
const MIN_SCORE_IN_CERT = 0.10;  // 종목이 특정된 경우
const MIN_SCORE_GLOBAL  = 0.30;  // 종목 미특정 상태에서 후보를 추릴 때

const SYNONYMS_DICT = {
  "포크레인": "굴착기",
  "포클레인": "굴착기",
  "굴삭기": "굴착기",
  "요보사": "요양보호사",
  "한조기": "한식조리기능사",
  "개사": "공인중개사",
  "공개사": "공인중개사",
  "손평사": "손해평가사",
  "지게차면허": "지게차운전기능사",
  "전기기사": "전기기능사"
};

// 질의에서 자격증 종목을 식별하기 위한 사전 (값은 FAQ 데이터의 cert 필드와 일치)
const CERT_ALIASES = {
  "공인중개사":  ["공인중개사", "중개사", "개사", "공개사", "부동산중개"],
  "요양보호사":  ["요양보호사", "요보사", "요양사"],
  "굴착기":      ["굴착기", "굴삭기", "포크레인", "포클레인"],
  "전기":        ["전기기능사", "전기기사", "전기산업기사", "전기"],
  "위생사":      ["위생사"],
  "지게차":      ["지게차운전기능사", "지게차면허", "지게차"],
  "한식조리":    ["한식조리기능사", "한식조리", "한조기", "조리기능사", "한식"],
  "손해평가사":  ["손해평가사", "손평사"]
};

function expandSynonyms(text) {
  let expanded = text;
  for (const [short, full] of Object.entries(SYNONYMS_DICT)) {
    const regex = new RegExp(short, 'gi');
    expanded = expanded.replace(regex, full);
  }
  return expanded;
}

// 질의에서 자격증 종목을 찾는다. 가장 길게 일치하는 별칭을 채택한다.
// (예: "전기기능사"가 "전기"보다 우선)
function detectCert(question) {
  const expanded = expandSynonyms(question);
  let matched = null;
  let matchedLength = 0;
  for (const [cert, aliases] of Object.entries(CERT_ALIASES)) {
    for (const alias of aliases) {
      if ((expanded.includes(alias) || question.includes(alias)) && alias.length > matchedLength) {
        matched = cert;
        matchedLength = alias.length;
      }
    }
  }
  return matched;
}

// 문서를 색인용 텍스트 한 덩어리로 만든다.
// qna_board: title/body/reply / phone: opening + exchanges[{caller, staff}]
function makeTextBlob(doc) {
  const parts = [doc.cert, doc.category, doc.title, doc.body, doc.reply, doc.opening];
  if (Array.isArray(doc.exchanges)) {
    for (const ex of doc.exchanges) parts.push(ex.caller, ex.staff, ex.topic);
  }
  return parts.filter(Boolean).join(' ');
}

// 문서에서 질의에 가장 가까운 답변 한 줄을 고른다.
// 전화 상담 문서는 여러 문답이 들어 있으므로 질의와 가장 가까운 문답을 선택한다.
function pickReply(doc, queryVec, queryNorm) {
  if ((doc.reply || '').trim()) return doc.reply;

  if (Array.isArray(doc.exchanges) && doc.exchanges.length) {
    let best = null, bestScore = -1;
    for (const ex of doc.exchanges) {
      if (!ex.staff) continue;
      const tf = computeTF(tokenize(`${ex.caller || ''} ${ex.topic || ''}`));
      const vec = {};
      let norm = 0;
      for (const t in tf) { vec[t] = tf[t] * (IDF[t] || 0); norm += vec[t] * vec[t]; }
      norm = Math.sqrt(norm);
      let dot = 0;
      for (const t in queryVec) if (vec[t]) dot += queryVec[t] * vec[t];
      const score = (queryNorm && norm) ? dot / (queryNorm * norm) : 0;
      if (score > bestScore) { bestScore = score; best = ex.staff; }
    }
    if (best) return best;
  }
  return null;
}

// 문서 제목 (전화 상담 문서는 제목이 없으므로 종목·유형으로 만든다)
function docTitle(doc) {
  if ((doc.title || '').trim()) return doc.title;
  if (doc.category) return `${doc.category} 상담 (전화)`;
  return '상담 기록';
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
  for (const token in tf) {
    tf[token] = tf[token] / totalTerms;
  }
  return tf;
}

// IDF (Inverse Document Frequency) 계산
function computeIDF(allDocTF) {
  const docFreq = {};
  const totalDocs = allDocTF.length;

  for (const tf of allDocTF) {
    for (const token of new Set(Object.keys(tf))) {
      docFreq[token] = (docFreq[token] || 0) + 1;
    }
  }

  const idf = {};
  for (const token in docFreq) {
    idf[token] = Math.log((totalDocs + 1) / (docFreq[token] + 1));
  }
  return idf;
}

// 문서 벡터와 크기를 미리 만들어 둔다 (질의마다 다시 만들지 않기 위해)
function buildIndex() {
  IDF = computeIDF(docTermFreq);
  docVectors = docTermFreq.map(tf => {
    const v = {};
    for (const token in tf) v[token] = tf[token] * (IDF[token] || 0);
    return v;
  });
  docNorms = docVectors.map(v => {
    let sum = 0;
    for (const token in v) sum += v[token] * v[token];
    return Math.sqrt(sum);
  });
}

// 질의 벡터와 i번째 문서 벡터의 코사인 유사도
function cosineSimilarity(queryVec, queryNorm, i) {
  const docVec = docVectors[i];
  let dotProduct = 0;
  for (const token in queryVec) {
    if (docVec[token]) dotProduct += queryVec[token] * docVec[token];
  }
  const denom = queryNorm * docNorms[i];
  return denom === 0 ? 0 : dotProduct / denom;
}

function buildQueryVector(question) {
  const tokens = tokenize(expandSynonyms(question));
  const tf = computeTF(tokens);
  const vec = {};
  for (const token in tf) vec[token] = tf[token] * (IDF[token] || 0);
  let norm = 0;
  for (const token in vec) norm += vec[token] * vec[token];
  return { vec, norm: Math.sqrt(norm) };
}

/**
 * 검색 결과
 *  - { cert, needCert: false, results: [[score, doc], ...] }
 *  - { cert: null, needCert: true, candidates: [자격증명...] }  → 되물어야 하는 경우
 */
function retrieve(question, topK = 3) {
  if (!FAQ.length || !docVectors.length) {
    return { cert: null, needCert: false, results: [] };
  }

  const { vec, norm } = buildQueryVector(question);
  const cert = detectCert(question);

  // 1) 종목이 식별된 경우: 해당 종목 문서 안에서만 찾는다
  if (cert) {
    const scored = [];
    for (let i = 0; i < FAQ.length; i++) {
      if (FAQ[i].cert !== cert) continue;
      scored.push([cosineSimilarity(vec, norm, i), FAQ[i]]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    return {
      cert,
      needCert: false,
      results: scored.slice(0, topK).filter(item => item[0] >= MIN_SCORE_IN_CERT)
    };
  }

  // 2) 종목이 식별되지 않은 경우: 후보 종목만 뽑아 되묻는다
  const scored = [];
  for (let i = 0; i < FAQ.length; i++) {
    scored.push([cosineSimilarity(vec, norm, i), FAQ[i]]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, 5).filter(item => item[0] >= MIN_SCORE_GLOBAL);

  if (top.length === 0) {
    return { cert: null, needCert: false, results: [] };
  }
  return {
    cert: null,
    needCert: true,
    candidates: [...new Set(top.map(item => item[1].cert))],
    results: []
  };
}

async function answerQuestion(question) {
  const found = retrieve(question);

  // 어느 자격증인지 모르면 답을 만들지 않고 되묻는다
  if (found.needCert) {
    return {
      status: 'NEED_CERT',
      answer: `어느 자격증에 대한 질문인지 알려주세요. (${found.candidates.join(' · ')})`,
      source: '종목 확인 필요',
      score: 0
    };
  }

  if (found.results.length === 0) {
    return {
      status: 'UNKNOWN',
      answer: '제공된 FAQ에서 확인할 수 없는 내용입니다.',
      source: '없음',
      score: 0
    };
  }

  // 답변을 만들 수 있는 첫 번째 결과를 고른다
  const { vec, norm } = buildQueryVector(question);
  let picked = null;
  for (const [score, doc] of found.results) {
    const reply = pickReply(doc, vec, norm);
    if (reply) { picked = [score, doc, reply]; break; }
  }
  if (!picked) {
    return {
      status: 'UNKNOWN',
      answer: '제공된 FAQ에서 확인할 수 없는 내용입니다.',
      source: '없음',
      score: 0
    };
  }
  const [bestScore, bestDoc, fallbackReply] = picked;
  const title = docTitle(bestDoc);
  const cert = bestDoc.cert || '?';

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
      docTermFreq = FAQ.map(doc => computeTF(tokenize(makeTextBlob(doc))));

      // IDF·문서 벡터 선계산 (질의마다 다시 만들지 않는다)
      buildIndex();

      faqLoaded = true;
      console.log(`✓ FAQ 로드 완료: ${FAQ.length}개 항목 (Stage7 - TF-IDF + 종목 필터)`);
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
