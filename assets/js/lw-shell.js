(() => {
  const assistantPage = /\/assistant\.html$/i.test(location.pathname);
  const indexPage = /\/(?:index\.html)?$/i.test(location.pathname);
  const utilityPage = /\/(?:library|install-books)\.html$/i.test(location.pathname);
  const params = new URLSearchParams(location.search);
  const surface = params.get('surface') || (assistantPage ? 'campaign' : 'library');

  function navLink(label, href, active) {
    return '<a href="' + href + '"' + (active ? ' aria-current="page"' : '') + '>' + label + '</a>';
  }

  function campaignLabel(payload) {
    const state = payload?.state || {};
    const character = state.Character || {};
    const book = Number(character.BookNumber);
    const section = Number(state.CurrentSection);
    if (Number.isInteger(book) && Number.isInteger(section)) return 'Book ' + book + ' · section ' + section;
    return 'No active campaign';
  }

  function addGlobalNav() {
    const active = assistantPage ? surface : (utilityPage ? 'library' : 'library');
    const nav = document.createElement('nav');
    nav.className = 'lw-global-nav';
    nav.setAttribute('aria-label', 'Application navigation');
    nav.innerHTML =
      '<a class="lw-global-nav__brand" href="index.html"><span class="lw-global-nav__mark"></span><span>Lone Wolf</span></a>' +
      '<div class="lw-global-nav__links">' +
      navLink('Library', 'index.html', active === 'library') +
      navLink('Campaign', 'assistant.html?surface=campaign&resume=1', active === 'campaign') +
      navLink('Reader', 'assistant.html?surface=reader&resume=1', active === 'reader') +
      navLink('Tools', 'assistant.html?surface=tools&resume=1', active === 'tools') +
      navLink('Console', 'assistant.html?surface=tools&console=1&resume=1', active === 'console') +
      navLink('Settings', 'assistant.html?surface=tools&tool=settings&resume=1', active === 'settings') +
      '</div><span class="lw-global-nav__campaign" data-lw-campaign-status>Loading campaign</span>';
    document.body.prepend(nav);
    return nav;
  }

  function addAssistantNav() {
    const header = document.querySelector('body > header');
    if (!header) return null;
    const nav = document.createElement('nav');
    nav.className = 'lw-inline-nav';
    nav.setAttribute('aria-label', 'Application navigation');
    nav.innerHTML =
      navLink('Library', 'index.html', false) +
      navLink('Campaign', 'assistant.html?surface=campaign&resume=1', surface === 'campaign') +
      navLink('Reader', 'assistant.html?surface=reader&resume=1', surface === 'reader') +
      navLink('Tools', 'assistant.html?surface=tools&resume=1', surface === 'tools') +
      navLink('Console', 'assistant.html?surface=tools&console=1&resume=1', params.get('console') === '1') +
      navLink('Settings', 'assistant.html?surface=tools&tool=settings&resume=1', params.get('tool') === 'settings');
    const title = header.querySelector('h1');
    if (title) title.insertAdjacentElement('afterend', nav);
    else header.prepend(nav);
    return header;
  }

  function markCurrentBook(payload) {
    if (!indexPage) return;
    const state = payload?.state || {};
    const bookNumber = Number(state?.Character?.BookNumber);
    const section = Number(state?.CurrentSection);
    if (!Number.isInteger(bookNumber)) return;
    const card = document.querySelector('[data-book-number="' + bookNumber + '"]');
    if (!card || card.querySelector('.lw-current-book-status')) return;
    card.classList.add('lw-current-book');
    const status = document.createElement('span');
    status.className = 'lw-current-book-status';
    status.textContent = Number.isInteger(section) ? 'Reading · section ' + section : 'Reading';
    const title = card.querySelector('strong');
    if (title) title.insertAdjacentElement('afterend', status);
  }

  function prepareLibrary(payload) {
    if (!indexPage) return;
    document.dispatchEvent(new CustomEvent('lonewolf:campaign-state', { detail: payload }));
  }

  function syncCampaignStatus(payload) {
    const label = campaignLabel(payload);
    document.querySelectorAll('[data-lw-campaign-status]').forEach((node) => { node.textContent = label; });
    markCurrentBook(payload);
    prepareLibrary(payload);
    renderProductionContext(payload);
  }

  function renderProductionContext(payload) {
    if (!assistantPage) return;
    const target = document.getElementById('productionContext');
    if (!target) return;
    const state = payload?.state || {};
    const character = state.Character || {};
    const book = Number(character.BookNumber);
    const section = Number(state.CurrentSection);
    const title = typeof window.bookByNumber === 'function'
      ? window.bookByNumber(book)?.title
      : '';
    const readableBook = Number.isInteger(book) ? 'Book ' + book + (title ? ' · ' + title : '') : 'Current campaign';
    const readableSection = Number.isInteger(section) ? 'Section ' + section : 'Preparing campaign';
    if (surface === 'tools') {
      target.innerHTML = '<div><span class="lw-production-context__eyebrow">Campaign tools</span><h2>Everything that supports this adventure</h2><p>' + readableBook + ' · ' + readableSection + '</p></div><div class="lw-production-context__actions"><a href="assistant.html?surface=campaign&resume=1">Return to campaign</a><a href="assistant.html?surface=reader&resume=1">Reader view</a></div>';
      return;
    }
    if (surface === 'reader') {
      target.innerHTML = '<div><span class="lw-production-context__eyebrow">Focused reader</span><h2>' + readableBook + '</h2><p>' + readableSection + ' · your campaign stays live while you read.</p></div><div class="lw-production-context__actions"><a href="assistant.html?surface=campaign&resume=1">Campaign desk</a><a href="assistant.html?surface=tools&resume=1">Tools</a><button type="button" data-console-drawer-open>Console</button></div>';
      return;
    }
    target.innerHTML = '<div><span class="lw-production-context__eyebrow">Current campaign</span><h2>' + readableBook + '</h2><p>' + readableSection + ' · choose the next legal action from the book.</p></div><div class="lw-production-context__actions"><a href="assistant.html?surface=reader&resume=1">Reader view</a><a href="assistant.html?surface=tools&resume=1">Campaign tools</a><button type="button" data-console-drawer-open>Console</button></div>';
  }

  function bindConsoleDrawer() {
    if (!assistantPage) return;
    const drawer = document.getElementById('consoleDrawer');
    const frame = document.getElementById('consoleDrawerFrame');
    if (!drawer || !frame) return;
    document.addEventListener('click', (event) => {
      if (event.target.closest('[data-console-drawer-open]')) {
        frame.src = 'assistant.html?surface=tools&console=1&resume=1&embedded=1';
        drawer.hidden = false;
      }
      if (event.target.closest('[data-console-drawer-close]')) {
        drawer.hidden = true;
        frame.removeAttribute('src');
      }
    });
  }

  function boot() {
    document.body.classList.add(assistantPage ? 'lw-shell-assistant' : (utilityPage ? 'lw-shell-utility' : 'lw-shell-index'));
    document.body.classList.add('lw-surface-' + surface);
    if (assistantPage) addAssistantNav();
    else addGlobalNav();
    bindConsoleDrawer();
    fetch('/api/state', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => { if (payload) syncCampaignStatus(payload); })
      .catch(() => {});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
