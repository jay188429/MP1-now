import fetch from 'node-fetch';

// FAQ 데이터 (파일 읽기 대신 직접 포함)
const FAQ = [
  {
    "id": 1,
    "cert": "한식조리기능사",
    "title": "한식조리기능사 시험비",
    "keywords": ["한식", "시험비", "비용", "접수료"],
    "text": "한식조리기능사 시험비는 실기 70,000원, 필기 14,500원입니다."
  },
  {
    "id": 2,
    "cert": "사회복지사",
    "title": "사회복지사 시험 과목",
    "keywords": ["사회복지사", "과목", "시험"],
    "text": "사회복지사 2급 필기시험 과목은 사회복지기초, 인간행동과사회환경, 사회복지정책론, 사회복지법제, 사회복지실천론, 사회복지실천기술론 등 6과목입니다."
  },
  {
    "id": 3,
    "cert": "전기기능사",
    "title": "전기기능사 시험 규정",
    "keywords": ["전기기능사", "계산기", "반입", "규정"],
    "text": "전기기능사 실기시험에서 계산기(일반용) 반입은 허용됩니다. 단, 프로그래밍 기능이 있는 계산기는 불허합니다."
  },
  {
    "id": 4,
    "cert": "공인중개사",
    "title": "공인중개사 환불 규정",
    "keywords": ["공인중개사", "환불", "반환", "규정"],
    "text": "공인중개사 자격시험 응시료는 합격자에 한해 자격증 발급 후 1년 이내 환불 신청이 가능합니다."
  },
  {
    "id": 5,
    "cert": "요양보호사",
    "title": "요양보호사 합격 기준",
    "keywords": ["요양보호사", "합격", "점수", "기준"],
    "text": "요양보호사 시험 합격 기준은 필기시험 100점 만점에 60점 이상, 실기시험도 100점 만점에 60점 이상입니다."
  }
];

function tokenize(text) {
  const tokens = text.match(/[가-힣A-Za-z0-9]+/g) || [];
  return new Set(tokens.map(t => t.toLowerCase()));
}

function retrieve(question, topK = 3, minScore = 2) {
  const q = tokenize(question);
  const ranked = [];

  for (const row of FAQ) {
    const keywordHits = row.keywords.filter(
      key => question.toLowerCase().includes(key.toLowerCase())
    ).length * 2;

    const qTokens = tokenize(row.title + ' ' + row.text);
    const overlap = Array.from(q).filter(token => qTokens.has(token)).length;
    
    const score = keywordHits + overlap;
    ranked.push([score, row]);
  }

  ranked.sort((a, b) => b[0] - a[0]);
  return ranked.slice(0, topK).filter(item => item[0] >= minScore);
}

async function callGemini(prompt) {
  const apiKey = process.env.GOOGLE_API_KEY;
  if (!apiKey) throw new Error('GOOGLE_API_KEY not set');

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent';
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-goog-api-key': apiKey
    },
    body: JSON.stringify({
      contents: [{
        parts: [{ text: prompt }]
      }]
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Gemini API error: ${response.status} - ${text}`);
  }

  const data = await response.json();
  return data.candidates[0].content.parts[0].text.trim();
}

function buildPrompt(question, document) {
  return `당신은 자격증 시험 접수 FAQ 상담원입니다.
아래 근거 안에서만 답하세요. 근거에 없는 내용을 만들지 마세요.
근거로 답할 수 없으면 정확히 UNKNOWN이라고 답하세요.

[질문]
${question}

[근거]
${document.text}

한국어 두 문장 이내로 답하세요.`;
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
  
  try {
    const generated = await callGemini(buildPrompt(question, bestDoc));

    if (!generated || generated.toUpperCase() === 'UNKNOWN') {
      return {
        status: 'UNKNOWN',
        answer: '제공된 FAQ에서 확인할 수 없는 내용입니다.',
        source: '없음',
        score: bestScore
      };
    }

    return {
      status: 'ANSWERED',
      answer: generated,
      source: `${bestDoc.cert} - ${bestDoc.title}`,
      score: bestScore
    };
  } catch (error) {
    return {
      status: 'ERROR',
      answer: `오류: ${error.message}`,
      source: '없음',
      score: bestScore
    };
  }
}

export default async function handler(req, res) {
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
    const result = await answerQuestion(message);
    return res.status(200).json(result);
  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({ error: error.message });
  }
}
