(() => {
  'use strict';
  const search = document.getElementById('search');
  const range = document.getElementById('date-range');
  const groups = [...document.querySelectorAll('.day-group')];
  const papers = [...document.querySelectorAll('.paper')].map(el => ({el, topic: el.dataset.topic, date: el.closest('.day-group').dataset.date, text: el.textContent.toLocaleLowerCase()}));
  const dates = groups.map(el => el.dataset.date).sort();
  const latest = dates.at(-1);
  let topic = 'all', pageLimit = 40;
  const topics = [...new Set(papers.map(p => p.topic))];
  const filters = document.getElementById('topic-filters');
  for (const name of ['all', ...topics]) {
    const button = document.createElement('button');
    button.type = 'button'; button.dataset.topic = name; button.setAttribute('aria-pressed', String(name === topic));
    button.append(document.createTextNode(name === 'all' ? 'All topics' : name));
    const count = document.createElement('span');count.textContent = papers.filter(p => name === 'all' || p.topic === name).length.toLocaleString();button.append(count);
    button.addEventListener('click', () => {topic = name; pageLimit = 40; render();}); filters.append(button);
  }
  document.getElementById('collection-count').textContent = `${papers.length.toLocaleString()} papers · ${topics.length} ${topics.length === 1 ? "topic" : "topics"}`;
  document.getElementById('collection-dates').textContent = dates.length ? `${dates[0]} — ${latest}` : 'No saved papers';
  const more = document.getElementById('load-more');
  function render() {
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const cutoff = range.value === 'all' || !latest ? '' : new Date(Date.parse(latest + 'T00:00:00Z') - (Number(range.value)-1)*86400000).toISOString().slice(0,10);
    const matches = papers.filter(p => (topic === 'all' || topic === p.topic) && p.date >= cutoff && terms.every(t => p.text.includes(t)));
    const shown = new Set(matches.slice(0,pageLimit));
    for (const p of papers) p.el.hidden = !shown.has(p);
    for (const group of groups) group.hidden = ![...group.querySelectorAll('.paper')].some(el => !el.hidden);
    for (const b of filters.children) b.setAttribute('aria-pressed', String(b.dataset.topic === topic));
    document.getElementById('results-count').textContent = `${matches.length.toLocaleString()} ${matches.length === 1 ? 'paper' : 'papers'}${terms.length ? ' matching your search' : ' in your selection'}`;
    document.getElementById('empty-state').hidden = matches.length > 0;
    more.hidden = matches.length <= pageLimit;
    document.getElementById('page-count').textContent = matches.length ? `Showing ${Math.min(pageLimit,matches.length)} of ${matches.length.toLocaleString()}` : '';
  }
  search.addEventListener('input', () => {pageLimit = 40; render();});
  range.addEventListener('change', () => {pageLimit = 40; render();});
  more.addEventListener('click', () => {pageLimit += 40; render();});
  document.getElementById('reset-filters').addEventListener('click', () => {search.value='';range.value='all';topic='all';pageLimit=40;render();});
  const toggle = document.getElementById('theme-toggle');
  let theme = 'light';
  try {theme = localStorage.getItem('myarxiv-theme') || 'light';} catch {}
  function setTheme(value) {theme = value; document.documentElement.dataset.theme=value;toggle.textContent=value==='dark'?'Light mode':'Dark mode';try {localStorage.setItem('myarxiv-theme',value);} catch {}}
  toggle.addEventListener('click', () => setTheme(theme === 'dark' ? 'light' : 'dark'));
  for (const details of document.querySelectorAll('.paper details')) {
    details.addEventListener('toggle', () => {
      if (details.open && window.renderMathInElement && !details.dataset.mathRendered) {
        window.renderMathInElement(details.querySelector('.abstract'), {delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});
        details.dataset.mathRendered = 'true';
      }
    });
  }
  setTheme(theme); render();
})();
