const fs = require('fs');
const path = require('path');

const raw = fs.readFileSync(path.join(__dirname, '..', 'public', 'faq_combined.jsonl'), 'utf8');
global.fetch = async () => ({ ok: true, status: 200, text: async () => raw });
const source = fs.readFileSync(path.join(__dirname, 'faq_after.js'), 'utf8') +
  '\nmodule.exports.__t={faqPromise,answerQuestion,detectCert,get FAQ(){return FAQ},hide(i){const v=docVectors[i],n=docNorms[i];docVectors[i]={};docNorms[i]=0;return()=>{docVectors[i]=v;docNorms[i]=n}}};';
const moduleShim = { exports: {} };
new Function('module', 'exports', 'require', 'console', source)(moduleShim, moduleShim.exports, require, { log() {}, error() {} });
const chatbot = moduleShim.exports.__t;

(async () => {
  await chatbot.faqPromise;
  const cases = chatbot.FAQ.map((doc, i) => ({ doc, i, question: (doc.body || '').trim() }))
    .filter(item => item.doc.channel === 'qna_board' && item.question)
    .slice(0, 800);
  const result = { total: cases.length, answered: 0, needCert: 0, unknown: 0, averageMs: 0 };
  let elapsed = 0;
  for (const item of cases) {
    const restore = chatbot.hide(item.i);
    const start = process.hrtime.bigint();
    const answer = await chatbot.answerQuestion(item.question);
    elapsed += Number(process.hrtime.bigint() - start) / 1e6;
    restore();
    if (answer.status === 'FALLBACK_ANSWERED') result.answered++;
    else if (answer.status === 'NEED_CERT') result.needCert++;
    else result.unknown++;
  }
  result.averageMs = Number((elapsed / cases.length).toFixed(2));
  console.log(JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(__dirname, 'result_800.txt'), JSON.stringify(result, null, 2) + '\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
