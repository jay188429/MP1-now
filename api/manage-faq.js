// FAQ 관리 API (추가/삭제)

let FAQ = [];
let faqLoaded = false;

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
      faqLoaded = true;
      console.log(`✓ FAQ 로드 완료: ${FAQ.length}개 항목`);
    }
  } catch (error) {
    console.error('FAQ 로드 오류:', error.message);
  }
}

const faqPromise = loadFAQ();

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // FAQ 로드 확인
  if (!faqLoaded) {
    await faqPromise;
  }
  if (!faqLoaded || FAQ.length === 0) {
    await loadFAQ();
  }

  // GET: FAQ 통계
  if (req.method === 'GET') {
    return res.status(200).json({
      total: FAQ.length,
      certs: [...new Set(FAQ.map(f => f.cert))],
      lastUpdated: new Date().toISOString()
    });
  }

  // POST: FAQ 추가 (로컬 메모리, 영속성 없음)
  if (req.method === 'POST') {
    const { cert, category, title, reply } = req.body;

    if (!cert || !title || !reply) {
      return res.status(400).json({
        error: 'cert, title, reply는 필수입니다'
      });
    }

    // 메모리에만 추가 (실제 저장은 GitHub에 커밋 필요)
    const newId = Math.max(...FAQ.map(f => f.id || 0), 0) + 1;
    const newFAQ = {
      id: newId,
      cert,
      category: category || '',
      title,
      body: '',
      reply,
      channel: 'admin_added'
    };

    FAQ.push(newFAQ);

    return res.status(201).json({
      success: true,
      message: 'FAQ가 추가되었습니다 (메모리에만 저장됨, GitHub 커밋 필요)',
      id: newId,
      total: FAQ.length
    });
  }

  // DELETE: FAQ 삭제
  if (req.method === 'DELETE') {
    const { id } = req.body;

    if (!id) {
      return res.status(400).json({ error: 'id는 필수입니다' });
    }

    const beforeLen = FAQ.length;
    FAQ = FAQ.filter(f => f.id !== id);

    if (FAQ.length === beforeLen) {
      return res.status(404).json({ error: 'FAQ ID를 찾을 수 없습니다' });
    }

    return res.status(200).json({
      success: true,
      message: 'FAQ가 삭제되었습니다 (메모리에서만 삭제됨)',
      total: FAQ.length
    });
  }

  return res.status(405).json({ error: 'Method not allowed' });
};
