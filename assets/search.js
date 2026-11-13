'use strict';
const container = document.getElementById('projects');
const cards = Array.from(container.querySelectorAll('article'));
const fields = ['search', 'language', 'license', 'status', 'sort'];
const inputs = Object.fromEntries(fields.map(k => [k, document.getElementById(k)]));
const params = new URLSearchParams(location.search);
for (const k of fields) if (params.has(k)) inputs[k].value = params.get(k);
let lastOrder = null;
function apply() {
  const query = inputs.search.value.trim().toLowerCase();
  let count = 0;
  for (const card of cards) {
    const match = query.split(/\s+/).every(term => card.dataset.search.includes(term)) && ['language', 'license', 'status'].every(k => !inputs[k].value || card.dataset[k] === inputs[k].value);
    card.hidden = !match;
    if (match) count++;
  }
  const order = inputs.sort.value;
  if (order !== lastOrder) {
    cards.sort((a, b) => order === 'stars' ? Number(b.dataset.stars) - Number(a.dataset.stars) : order === 'updated' || order === 'starred' ? b.dataset[order].localeCompare(a.dataset[order]) : a.dataset.name.localeCompare(b.dataset.name));
    const fragment = document.createDocumentFragment();
    for (const card of cards) fragment.append(card);
    container.append(fragment);
    lastOrder = order;
  }
  document.getElementById('count').textContent = `${count.toLocaleString()} projects`;
  document.getElementById('empty').hidden = count !== 0;
  const state = new URLSearchParams();
  for (const k of fields) if (inputs[k].value && !(k === 'sort' && inputs[k].value === 'name')) state.set(k, inputs[k].value);
  history.replaceState(null, '', location.pathname + (state.size ? '?' + state : ''));
}
let timer;
for (const k of fields) inputs[k].addEventListener(k === 'search' ? 'input' : 'change', () => {clearTimeout(timer); timer = setTimeout(apply, 120);});
apply();
