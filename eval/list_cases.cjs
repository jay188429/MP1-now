const fs=require('fs'),path=require('path');
const RAW=fs.readFileSync('public/faq_combined.jsonl','utf8');
global.fetch=async()=>({ok:true,status:200,text:async()=>RAW});
const src=fs.readFileSync('eval/faq_after.js','utf8')+'\nmodule.exports.__t={faqPromise,answerQuestion,detectCert,get FAQ(){return FAQ},hide(i){const v=docVectors[i],n=docNorms[i];docVectors[i]={};docNorms[i]=0;return()=>{docVectors[i]=v;docNorms[i]=n}}};';
const m={exports:{}};new Function('module','exports','require','console',src)(m,m.exports,require,{log(){},error(){}});const A=m.exports.__t;
(async()=>{await A.faqPromise;const F=A.FAQ;
for(let i=0;i<F.length;i++){const d=F[i];if(d.channel!=='qna_board')continue;const q=(d.body||'').trim();const c=A.detectCert(q);if(!c)continue;
const r=A.hide(i);const a=await A.answerQuestion(q);r();
if(a.status==='FALLBACK_ANSWERED'){const got=a.source.split(' - ')[0];if(got!==d.cert)console.log('WRONG',JSON.stringify(q),'label',d.cert,'detected',c,'got',got)}
else if(a.status!=='FALLBACK_ANSWERED')console.log(a.status,JSON.stringify(q),'label',d.cert,'detected',c)}})();
