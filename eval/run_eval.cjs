// MP1 FAQ 챗봇 재측정 스크립트 (고치기 전 / 고친 뒤 비교)
//
// 질문지: 강사 제공 교육용 게시판 문의 1,203건의 문의 본문(body)
// 정답:   질문에 자격증 이름이 있으면 → 그 자격증 (사용자가 물은 자격증)
//         질문에 자격증 이름이 없으면 → 문의에 붙어 있는 종목 라벨(cert)
//         ※ 라벨이 질문 내용과 다른 문의가 14건 있어(예: 한식조리 질문에 '전기' 라벨) 따로 셈
// 규칙:   질문으로 쓴 문의 자신의 문서는 검색 대상에서 빼고 채점 (자기 답을 베끼지 않게)
//
// 실행:  node eval/run_eval.cjs      (senior-cert-faq-chatbot 폴더에서)
const fs = require('fs');
const path = require('path');

const DATA = path.join(__dirname, '..', 'public', 'faq_combined.jsonl');
const RAW = fs.readFileSync(DATA, 'utf8');

// 두 버전 모두 배포 주소에서 데이터를 받아오므로, 로컬 파일을 돌려주도록 바꿔 끼운다
global.fetch = async () => ({ ok: true, status: 200, text: async () => RAW });

function load(file, exportLine) {
  const src = fs.readFileSync(path.join(__dirname, file), 'utf8') + '\n' + exportLine;
  const m = { exports: {} };
  new Function('module', 'exports', 'require', 'console', src)(m, m.exports, require, { log() {}, error() {} });
  return m.exports.__t;
}

const before = load('faq_before.js',
  'module.exports.__t = { faqPromise, retrieve, get FAQ(){return FAQ}, hide(i){const s=docTermFreq[i]; docTermFreq[i]={}; return ()=>{docTermFreq[i]=s}} };');
const after = load('faq_after.js',
  'module.exports.__t = { faqPromise, retrieve, answerQuestion, detectCert, get FAQ(){return FAQ}, hide(i){const v=docVectors[i],n=docNorms[i]; docVectors[i]={}; docNorms[i]=0; return ()=>{docVectors[i]=v; docNorms[i]=n}} };');

(async () => {
  await before.faqPromise; await after.faqPromise;
  const FAQ = after.FAQ;
  const queries = FAQ.map((d, i) => ({ i, q: (d.body || '').trim(), cert: d.cert }))
                     .filter(x => d_ok(x));
  function d_ok(x) { return FAQ[x.i].channel === 'qna_board' && x.q; }

  const init = () => ({ n: 0, match: 0, wrong: 0, ask: 0, none: 0, noReply: 0 });
  const R = { before: { with: init(), without: init() }, after: { with: init(), without: init() } };
  let tB = 0, tA = 0, labelNoise = 0;
  const examples = [];

  for (const x of queries) {
    const named = after.detectCert(x.q);
    const grp = named ? 'with' : 'without';
    const truth = named || x.cert;
    if (named && named !== x.cert) labelNoise++;

    // 고치기 전
    let restore = before.hide(x.i);
    let t0 = process.hrtime.bigint();
    const rb = before.retrieve(x.q);
    tB += Number(process.hrtime.bigint() - t0) / 1e6;
    restore();
    const b = R.before[grp]; b.n++;
    if (!rb.length) b.none++;
    else {
      const top = rb[0][1];
      if (top.cert === truth) { b.match++; if (!(top.reply || top.text)) b.noReply++; }
      else { b.wrong++; if (examples.length < 5 && grp === 'with') examples.push({ q: x.q, 정답: truth, 기존1위: top.cert }); }
    }

    // 고친 뒤
    restore = after.hide(x.i);
    t0 = process.hrtime.bigint();
    const ra = await after.answerQuestion(x.q);
    tA += Number(process.hrtime.bigint() - t0) / 1e6;
    restore();
    const a = R.after[grp]; a.n++;
    if (ra.status === 'NEED_CERT') a.ask++;
    else if (ra.status === 'UNKNOWN') a.none++;
    else { const c = ra.source.split(' - ')[0]; if (c === truth) a.match++; else a.wrong++; }
  }

  const pct = (v, n) => n ? (100 * v / n).toFixed(1) + '%' : '-';
  const row = (name, r) => `${name}\t${r.n}건\t일치 ${pct(r.match, r.n)}\t오답 ${pct(r.wrong, r.n)}\t되묻기 ${pct(r.ask, r.n)}\t답 없음 ${pct(r.none, r.n)}` + (r.noReply ? `\t(일치했지만 답변 문장 없음 ${r.noReply}건)` : '');
  const answerable = FAQ.filter(d => (d.reply || d.text)).length;
  const answerableAfter = FAQ.filter(d => (d.reply || '').trim() || (Array.isArray(d.exchanges) && d.exchanges.some(e => e.staff))).length;

  const out = [
    `질문지: 게시판 문의 본문 ${queries.length}건 (강사 제공 교육용, 자기 문서 제외 채점)`,
    '',
    '[질문에 자격증 이름이 있음]',
    row('  고치기 전', R.before.with), row('  고친 뒤 ', R.after.with),
    '[질문에 자격증 이름이 없음]',
    row('  고치기 전', R.before.without), row('  고친 뒤 ', R.after.without),
    `  (질문에 적힌 자격증과 라벨이 다른 문의 ${labelNoise}건 — 질문에 적힌 자격증을 정답으로 채점)`,
    '',
    `답변 문장을 만들 수 있는 문서: 고치기 전 ${answerable}/${FAQ.length} (${pct(answerable, FAQ.length)}) → 고친 뒤 ${answerableAfter}/${FAQ.length} (${pct(answerableAfter, FAQ.length)})`,
    `질문 1건 평균 처리 시간: 고치기 전 ${(tB / queries.length).toFixed(2)} ms → 고친 뒤 ${(tA / queries.length).toFixed(2)} ms`,
    '',
    '고치기 전 오답 예시 (자격증 이름이 있는 질문):',
    ...examples.map(e => `  - "${e.q}"  정답 ${e.정답} → 기존 1위 ${e.기존1위}`),
  ].join('\n');
  console.log(out);
  fs.writeFileSync(path.join(__dirname, 'result.txt'), out + '\n');
})();
