const track = document.getElementById('newsTrack');
const status = document.getElementById('newsStatus');
const dateFormat = new Intl.DateTimeFormat('fa-IR', {
  timeZone:'Asia/Tehran', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'
});
let articles = [], active = 0, loading = false, offline = false;

function node(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text) element.textContent = text;
  return element;
}
function webUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}
function card(story) {
  const article = node('article', 'news-card');
  const copy = node('div', 'news-copy');
  const tags = (story.tags || []).map(tag => tag.replace(/^#/, '')).join(' · ');
  const date = new Date(story.published);
  const byline = [story.source, Number.isFinite(+date) && dateFormat.format(date)].filter(Boolean);
  copy.append(node('span','news-tags',tags), node('small','news-meta',byline.join('  /  ')),
    node('h3','',story.title), node('p','',story.summary));
  const source = node('a', 'news-source', 'خواندن در ' + story.source + ' ↗');
  source.href = webUrl(story.link);
  source.target = '_blank';
  source.rel = 'noopener noreferrer';
  copy.append(source);
  article.append(copy);
  if (webUrl(story.photo)) {
    const photo = node('img','news-image');
    photo.alt = '';
    photo.loading = 'lazy';
    photo.addEventListener('error', () => article.classList.add('no-photo'));
    photo.src = webUrl(story.photo);
    article.append(photo);
  } else article.classList.add('no-photo');
  return article;
}
function newsRow(story) {
  const link = node('a', 'news-row');
  link.href = webUrl(story.link);
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  const date = new Date(story.published);
  const meta = [story.source, Number.isFinite(+date) && dateFormat.format(date)].filter(Boolean);
  link.append(node('small','news-meta',meta.join(' · ')),node('strong','',story.title));
  return link;
}
function indicator() {
  document.getElementById('newsMore').hidden = articles.length < 2;
  const rows = document.getElementById('newsList').children;
  for (let i = 0; i < rows.length; i++) rows[i].hidden = i === active;
  // Only show useful state messages; never show redundant 'news N of M' labels.
  const label = offline
    ? (articles.length ? 'به‌روزرسانی خبرها در دسترس نیست.' : 'دریافت خبرها ممکن نیست.')
    : (articles.length ? '' : 'هنوز خبری منتشر نشده است.');
  status.hidden = !label;
  if (status.textContent !== label) status.textContent = label;
}
function go(index, smooth) {
  const target = track.children[index];
  if (!target) return;
  const offset = target.getBoundingClientRect().right - track.getBoundingClientRect().right;
  track.scrollBy({left:offset, behavior:smooth && !matchMedia('(prefers-reduced-motion: reduce)').matches ? 'smooth' : 'instant'});
}
track.addEventListener('scroll', () => {
  const right = track.getBoundingClientRect().right;
  let closest = Infinity;
  Array.from(track.children).forEach((item,i) => {
    const distance = Math.abs(item.getBoundingClientRect().right-right);
    if (distance < closest) { closest = distance; active = i; }
  });
  indicator();
}, {passive:true});

export async function refreshNews() {
  if (loading) return;
  loading = true;
  try {
    const response = await fetch('./data/news.json', {cache:'no-store'});
    if (!response.ok) throw Error();
    const items = (await response.json()).filter(s => s.title && webUrl(s.link)).slice(0,16);
    offline = false;
    if (JSON.stringify(items) !== JSON.stringify(articles)) {
      const oldId = active > 0 && articles[active]?.id;
      active = Math.max(0,items.findIndex(s => s.id === oldId));
      articles = items;
      track.replaceChildren(...articles.map(card));
      document.getElementById('newsList').replaceChildren(...articles.map(newsRow));
      go(active,false);
    }
  } catch { offline = true; }
  finally { loading = false; indicator(); }
}
