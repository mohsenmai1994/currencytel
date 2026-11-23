/* CurrencyTel v5: two market tools visible per page; RTL-safe paging. */
(() => {
  'use strict';
  const boot = () => {
    const track = document.getElementById('marketFeatureCards');
    const prev = document.getElementById('marketFeaturePrev');
    const next = document.getElementById('marketFeatureNext');
    const dots = document.getElementById('marketFeatureDots');
    if (!track || !prev || !next || !dots || track.dataset.carouselReady) return;
    track.dataset.carouselReady = 'true';
    const cards = Array.from(track.querySelectorAll('[data-market-feature]'));
    const perPage = 2;
    const pageCount = Math.ceil(cards.length / perPage);
    if (!cards.length) return;
    let page = 0;
    let frame = 0;
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const paint = () => {
      prev.disabled = page <= 0;
      next.disabled = page >= pageCount - 1;
      Array.from(dots.children).forEach((dot, n) => {
        if (n === page) dot.setAttribute('aria-current', 'true');
        else dot.removeAttribute('aria-current');
      });
    };
    // Use viewport-relative bounding boxes to work across RTL scrollLeft implementations.
    const nearest = () => {
      const right = track.getBoundingClientRect().right;
      let best = 0;
      let distance = Infinity;
      for (let n = 0; n < pageCount; n++) {
        const card = cards[n * perPage];
        if (!card) continue;
        const d = Math.abs(card.getBoundingClientRect().right - right);
        if (d < distance) { best = n; distance = d; }
      }
      page = best;
      paint();
    };
    const toPage = (n) => {
      page = Math.max(0, Math.min(pageCount - 1, n));
      paint();
      const target = cards[page * perPage];
      target?.scrollIntoView({
        behavior: reduceMotion?.matches ? 'instant' : 'smooth',
        inline: 'start', block: 'nearest'
      });
    };
    dots.replaceChildren();
    for (let n = 0; n < pageCount; n++) {
      const dot = document.createElement('button');
      dot.type = 'button';
      const group = cards.slice(n * perPage, (n + 1) * perPage);
      dot.setAttribute('aria-label', 'نمایش ابزارها: ' + group.map(c => c.querySelector('strong')?.textContent?.trim() || '').join(' و '));
      dot.addEventListener('click', () => toPage(n));
      dots.appendChild(dot);
    }
    prev.addEventListener('click', () => toPage(page - 1));
    next.addEventListener('click', () => toPage(page + 1));
    track.addEventListener('scroll', () => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => { frame = 0; nearest(); });
    }, {passive:true});
    track.addEventListener('keydown', event => {
      if (event.target !== track) return;
      if (event.key === 'ArrowLeft') { event.preventDefault(); toPage(page + 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); toPage(page - 1); }
      if (event.key === 'Home') { event.preventDefault(); toPage(0); }
      if (event.key === 'End') { event.preventDefault(); toPage(pageCount - 1); }
    });
    window.addEventListener('resize', () => {
      toPage(page);
    }, {passive:true});
    paint();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
