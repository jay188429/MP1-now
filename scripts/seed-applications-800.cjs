const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const config = fs.readFileSync(path.join(root, 'supabase-config.js'), 'utf8');
const url = config.match(/SUPABASE_URL\s*=\s*["']([^"']+)/)?.[1];
const key = config.match(/SUPABASE_ANON_KEY\s*=\s*["']([^"']+)/)?.[1];
if (!url || !key) throw new Error('supabase-config.js의 URL/key를 읽지 못했습니다.');

const csv = fs.readFileSync(path.join(root, 'data', 'applications_import.csv'), 'utf8')
  .replace(/^\ufeff/, '').trim().split(/\r?\n/);
const headers = csv.shift().split(',');
const rows = csv.map(line => {
  const values = line.split(',');
  return Object.fromEntries(headers.map((header, i) => [header, values[i] ?? '']));
});
const marker = 'seed:applications-800';
const source = rows.slice(0, 800).map(row => ({
  name: row.name,
  phone: row.phone.replace(/\D/g, ''),
  certificate: row.certificate,
  birth: row.birth || null,
  address: row.address || null,
  received_at: new Date(row.received_at.replace(' ', 'T') + '+09:00').toISOString(),
  status: row.status || '접수완료',
  route: row.route || null,
  note: marker
}));

async function request(pathname, options = {}) {
  const response = await fetch(`${url}/rest/v1/${pathname}`, {
    ...options,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`${response.status} ${body}`);
  return body ? JSON.parse(body) : null;
}

(async () => {
  const existing = await request(`applications?select=phone&note=eq.${encodeURIComponent(marker)}&limit=1000`);
  const existingPhones = new Set((existing || []).map(row => row.phone));
  const pending = source.filter(row => !existingPhones.has(row.phone));

  for (let i = 0; i < pending.length; i += 100) {
    const batch = pending.slice(i, i + 100);
    await request('applications', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify(batch)
    });
    console.log(`적재 ${Math.min(i + batch.length, pending.length)}/${pending.length}`);
  }
  console.log(JSON.stringify({ target: 800, alreadyPresent: existingPhones.size, inserted: pending.length, totalSeeded: existingPhones.size + pending.length }));
})().catch(error => { console.error(error.message); process.exitCode = 1; });
