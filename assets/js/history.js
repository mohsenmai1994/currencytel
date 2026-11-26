/** Pure analytics on recorded, non-interpolated market observations. */
export const PERIODS = Object.freeze({
  '24h': {ms: 24 * 3600000, label: '۲۴ ساعت'},
  '7d': {ms: 7 * 86400000, label: '۷ روز'},
  '30d': {ms: 30 * 86400000, label: '۳۰ روز'},
  '90d': {ms: 90 * 86400000, label: '۹۰ روز'},
});
export function historyWindow(points, assetId, period='24h', now=Date.now()) {
  const chosen = PERIODS[period] || PERIODS['24h'];
  const start = now - chosen.ms;
  const seen = new Map();
  for (const point of points || []) {
    if (!point || typeof point !== 'object') continue;
    const t = Date.parse(point.at);
    if (!Number.isFinite(t) || t < start || t > now + 120000) continue;
    const raw = point.values?.[assetId];
    if (raw === null || raw === undefined || raw === '') continue;
    const value = Number(raw);
    if (Number.isFinite(value) && value > 0) seen.set(t, {t, value});
  }
  const entries = [...seen.values()].sort((a,b) => a.t-b.t);
  const first = entries[0], last = entries.at(-1);
  const values = entries.map(x => x.value);
  const difference = entries.length >= 2 ? last.value-first.value : null;
  const percent = difference !== null && first.value > 0 ? difference/first.value*100 : null;
  return {
    entries, start, end: now, period,
    min: values.length ? Math.min(...values) : null,
    max: values.length ? Math.max(...values) : null,
    first: first || null, last: last || null,
    difference, percent,
    coverage: entries.length >= 2 ? (last.t-first.t)/chosen.ms : 0,
  };
}
