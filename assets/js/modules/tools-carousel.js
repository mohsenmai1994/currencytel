/* CurrencyTel v6: swipeable two-card carousel, without visual arrow buttons. */
(() => {
  'use strict';
  const boot = () => {
    const track = document.getElementById('marketFeatureCards');
    const dots = document.getElementById('marketFeatureDots');
    if (!track || !dots || track.dataset.carouselReady) return;
    track.dataset.carouselReady = 'true';
    const cards = Array.from(track.querySelectorAll('[data-market-feature]'));
    const perPage = 2;
    const count = Math.ceil(cards.length / perPage);
    if (!cards.length) return;
    let page = 0;
    let frame = 0;
    const reduceMotion = matchMedia('(prefers-reduced-motion:reduce)');
    const paint = () => {
      Array.from(dots.children).forEach((dot, n) => {
        if (n === page) dot.setAttribute('aria-current','true');
        else dot.removeAttribute('aria-current');
      });
    };
    const nearest = () => {
      const right = track.getBoundingClientRect().right;
      let best = 0, distance = Infinity;
      for (let n = 0; n < count; n++) {
        const c = cards[n * perPage]; if (!c) continue;
        const d = Math.abs(c.getBoundingClientRect().right - right);
        if (d < distance) { best = n; distance = d; }
      }
      page = best; paint();
    };
    const toPage = n => {
      page = Math.max(0,Math.min(count-1,n)); paint();
      cards[page*perPage]?.scrollIntoView({
        behavior: reduceMotion.matches ? 'instant' : 'smooth',
        inline:'start',block:'nearest'
      });
    };
    dots.replaceChildren();
    for (let n = 0; n < count; n++) {
      const dot=document.createElement('button'); dot.type='button';
      const group=cards.slice(n*perPage,(n+1)*perPage);
      dot.setAttribute('aria-label','نمایش ابزارها: '+group.map(c=>c.querySelector('strong')?.textContent?.trim()||'').join(' و '));
      dot.addEventListener('click',()=>toPage(n)); dots.append(dot);
    }
    track.addEventListener('scroll',()=>{
      if(frame)cancelAnimationFrame(frame);
      frame=requestAnimationFrame(()=>{frame=0;nearest();});
    },{passive:true});
    track.addEventListener('keydown',event=>{
      if(event.target!==track)return;
      const keys={ArrowLeft:page+1,ArrowRight:page-1,Home:0,End:count-1};
      if(Object.hasOwn(keys,event.key)){event.preventDefault();toPage(keys[event.key]);}
    });
    window.addEventListener('resize',()=>{toPage(page);},{passive:true});
    paint();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
