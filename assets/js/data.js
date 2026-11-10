const MAX_ITEMS = 500;
function assertSnapshot(result) {
  if (!result || result.schema_version !== 2 || !Array.isArray(result.items)) throw new Error('فرمت داده بازار معتبر نیست.');
  if (result.items.length > MAX_ITEMS) throw new Error('تعداد داده‌ها نامعتبر است.');
  return result;
}
export async function getSnapshot(signal) {
  const response=await fetch('./data/market.json',{cache:'no-store',signal});
  if (!response.ok) throw new Error(`خطای دریافت داده بازار (${response.status})`);
  return assertSnapshot(await response.json());
}
export async function getHistory() {
  try {
    const r=await fetch('./data/history.json',{cache:'no-store'});
    if (!r.ok) return [];
    const data=await r.json();
    return Array.isArray(data.points)?data.points.slice(-336):[];
  } catch {return [];}
}
