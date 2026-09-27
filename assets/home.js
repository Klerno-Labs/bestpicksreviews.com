/* Progressive enhancement: every guide remains available when JavaScript is off. */
(() => {
  const search = document.querySelector('.bp-search');
  const input = document.getElementById('guide-search');
  const clear = document.getElementById('clear-search');
  const status = document.getElementById('search-status');
  const empty = document.getElementById('no-results');
  const guides = [...document.querySelectorAll('.bp-guide')];
  const categories = [...document.querySelectorAll('.bp-category')];
  if (!search || !input || !clear || !status || !empty) return;

  const normalize = (value) => value.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  function filter() {
    const words = normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const guide of guides) {
      const text = normalize(guide.dataset.search || guide.textContent || '');
      guide.hidden = !words.every((word) => text.includes(word));
      if (!guide.hidden) count += 1;
    }
    for (const category of categories) {
      category.hidden = ![...category.querySelectorAll('.bp-guide')].some((guide) => !guide.hidden);
    }
    empty.hidden = count !== 0;
    clear.hidden = input.value.length === 0;
    status.textContent = words.length
      ? `${count} ${count === 1 ? 'guide matches' : 'guides match'} your search.`
      : `Showing all ${guides.length} guides.`;
  }

  input.addEventListener('input', filter);
  clear.addEventListener('click', () => {
    input.value = '';
    filter();
    input.focus();
  });
  // Category jump links must work even after a search has hidden their section.
  for (const link of document.querySelectorAll('.bp-nav a, .bp-topic')) {
    link.addEventListener('click', () => {
      input.value = '';
      filter();
    });
  }
  search.hidden = false;
})();
