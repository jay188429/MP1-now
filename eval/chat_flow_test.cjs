// 챗봇 대화 흐름 점검 — 한 줄 질문 · 되묻기 후 이어 묻기 · 응시자격 · 근거 없음
// 실행: node eval/chat_flow_test.cjs  (배포 주소의 FAQ 데이터를 불러와 api/faq.js로 채점)
const handler = require('../api/faq.js');
function ask(message, context) {
  return new Promise(resolve => {
    const res = { setHeader() {}, status() { return { json: resolve, end: () => resolve(null) }; } };
    handler({ method: 'POST', body: { message, context } }, res);
  });
}
// [대화, 마지막 답변에 대한 기대]  expect: status 또는 source에 들어가야 할 문자열
const CASES = [
  [['공인중개사 응시자격'], { source: '공인중개사 응시자격' }],
  [['공인중개사 응시 자격이 어떻게 되나요?'], { source: '공인중개사 응시자격' }],
  [['공인중개사', '응시자격'], { source: '공인중개사 응시자격' }],
  [['공인중개사', '응시자격', '접수 기간'], { source: '접수 기간' }],
  [['접수 기간이 언제인가요?'], { status: 'NEED_CERT', answerHas: '위생사' }],
  [['접수 기간이 언제인가요?', '굴착기'], { source: '굴착기 시험 접수 기간' }],
  [['접수 기간이 언제인가요?', '공인중개사'], { source: '공인중개사 시험 접수 기간' }],
  [['공인중개사 접수 기간이 언제인가요?'], { source: '공인중개사 시험 접수 기간' }],
  [['요보사 자격 취득 방법'], { source: '요양보호사' }],
  [['위생사 응시자격'], { source: '위생사' }],
  [['굴착기 응시자격'], { status: 'UNKNOWN' }],
  [['오늘 점심 뭐 먹지?'], { status: 'UNKNOWN' }],
];
(async () => {
  let pass = 0;
  for (const [turns, exp] of CASES) {
    const ctx = []; let r;
    for (const m of turns) { r = await ask(m, ctx.slice(-8)); ctx.push(m); }
    const ok = (!exp.status || r.status === exp.status)
      && (!exp.source || (r.source || '').includes(exp.source))
      && (!exp.answerHas || (r.answer || '').includes(exp.answerHas));
    if (ok) pass++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${turns.join(' → ')}\n      ${r.status} | ${r.source}`);
  }
  console.log(`\n${pass} / ${CASES.length} 통과`);
  process.exit(pass === CASES.length ? 0 : 1);
})();
