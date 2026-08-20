import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const faqPath = path.join(__dirname, '../D23_FAQ_챗봇/stage1_local_basic');

// FAQ 데이터 로드
const FAQ = JSON.parse(
  fs.readFileSync(path.join(faqPath, 'faq.json'), 'utf-8')
);

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
    throw new Error(`Gemini API error: ${response.status}`);
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
    return res.status(500).json({ error: error.message });
  }
}
