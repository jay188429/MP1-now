// 사용법: node eval/try_query.cjs "질문"  → 고치기 전/후 1위 문서의 자격증을 보여 준다
const fs=require('fs'),path=require('path');
const RAW=fs.readFileSync(path.join(__dirname,'..','public','faq_combined.jsonl'),'utf8');
global.fetch=async()=>({ok:true,status:200,text:async()=>RAW});
function load(f,x){const m={exports:{}};new Function('module','exports','require','console',fs.readFileSync(path.join(__dirname,f),'utf8')+'\n'+x)(m,m.exports,require,{log(){},error(){}});return m.exports.__t}
const B=load('faq_before.js','module.exports.__t={faqPromise,retrieve}');
const A=load('faq_after.js','module.exports.__t={faqPromise,answerQuestion}');
(async()=>{await B.faqPromise;await A.faqPromise;
for(const q of process.argv.slice(2)){const rb=B.retrieve(q);const ra=await A.answerQuestion(q);
console.log(`Q: ${q}\n  고치기 전 1위: ${rb.length?rb[0][1].cert+' / '+(rb[0][1].title||rb[0][1].category):'없음'}\n  고친 뒤: ${ra.status} / ${ra.source}`)}})();
