// Node.js 18+ 내장 fetch 사용

let FAQ = [];
let faqLoaded = false;

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

  const model = process.env.GEMINI_MODEL || 'gemini-3.5-flash';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
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

async function loadFAQ() {
  try {
    const response = await fetch('https://mp1-now.vercel.app/faq.json');
    if (response.ok) {
      FAQ = await response.json();
      faqLoaded = true;
      console.log(`✓ FAQ 로드 완료: ${FAQ.length}개 항목`);
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
