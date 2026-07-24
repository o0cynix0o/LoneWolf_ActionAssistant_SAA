(function () {
  const STORAGE_KEYS = {
    titleBanner: 'lonewolf_redux.appearance.titleBanner.v1',
    coverArt: 'lonewolf_redux.appearance.coverArt.v1',
    theme: 'lonewolf_redux.appearance.theme.v1',
    readerStyleEnabled: 'lonewolf_redux.reader.styleEnabled.v1',
    readerTheme: 'lonewolf_redux.reader.theme.v1'
  };

  const defaults = {
    titleBanner: 'title1',
    coverArt: 'on',
    theme: 'kai-gold',
    readerStyleEnabled: 'off',
    readerTheme: 'original'
  };

  const titleBanners = {
    title1: { name: 'Classic Title', path: 'assets/images/title-banners/title1.png' },
    title2: { name: 'Red Banner', path: 'assets/images/title-banners/title2.png' },
    title3: { name: 'Painted Banner', path: 'assets/images/title-banners/title3.png' }
  };

  const themes = {
    'kai-gold': {
      '--lw-bg': '#10130e',
      '--lw-bg-soft': '#12160f',
      '--lw-panel': '#171b12',
      '--lw-panel-2': '#202617',
      '--lw-panel-3': '#26301b',
      '--lw-border': '#4e4528',
      '--lw-border-strong': '#6d5f35',
      '--lw-text': '#efe8d0',
      '--lw-muted': '#aeb091',
      '--lw-muted-2': '#d8d0b8',
      '--lw-accent': '#f2d27a',
      '--lw-accent-2': '#d1b865',
      '--lw-danger': '#ffb4a8',
      '--lw-danger-border': '#7e4038',
      '--lw-reader-shell': '#d8cfac',
      '--lw-reader-page': '#ffffe6',
      '--lw-shadow': 'rgba(0, 0, 0, 0.35)',
      '--lw-hero-glow': 'rgba(98, 78, 142, 0.34)'
    },
    'sommerswerd-dawn': {
      '--lw-bg': '#111313',
      '--lw-bg-soft': '#171918',
      '--lw-panel': '#1d211f',
      '--lw-panel-2': '#28302d',
      '--lw-panel-3': '#31413f',
      '--lw-border': '#556461',
      '--lw-border-strong': '#83918b',
      '--lw-text': '#f4f2e7',
      '--lw-muted': '#b9c1bb',
      '--lw-muted-2': '#d7dfd7',
      '--lw-accent': '#ffd36c',
      '--lw-accent-2': '#f0a94d',
      '--lw-danger': '#ffb6a4',
      '--lw-danger-border': '#8b4d42',
      '--lw-reader-shell': '#e0d8b6',
      '--lw-reader-page': '#fff8d8',
      '--lw-shadow': 'rgba(0, 0, 0, 0.36)',
      '--lw-hero-glow': 'rgba(240, 169, 77, 0.28)'
    },
    'durenor-sea': {
      '--lw-bg': '#0c1517',
      '--lw-bg-soft': '#102024',
      '--lw-panel': '#14282c',
      '--lw-panel-2': '#1c363b',
      '--lw-panel-3': '#244a50',
      '--lw-border': '#345d63',
      '--lw-border-strong': '#5b8589',
      '--lw-text': '#eef6ef',
      '--lw-muted': '#9fb9b5',
      '--lw-muted-2': '#d2e4df',
      '--lw-accent': '#ffd778',
      '--lw-accent-2': '#6fc3c7',
      '--lw-danger': '#ffb8a8',
      '--lw-danger-border': '#87473c',
      '--lw-reader-shell': '#d1dbc7',
      '--lw-reader-page': '#fffbe2',
      '--lw-shadow': 'rgba(0, 0, 0, 0.38)',
      '--lw-hero-glow': 'rgba(75, 164, 171, 0.30)'
    },
    'kalte-frost': {
      '--lw-bg': '#101416',
      '--lw-bg-soft': '#151d21',
      '--lw-panel': '#1b262b',
      '--lw-panel-2': '#26363d',
      '--lw-panel-3': '#304850',
      '--lw-border': '#49656c',
      '--lw-border-strong': '#7ca0a8',
      '--lw-text': '#eef7f8',
      '--lw-muted': '#adc4c8',
      '--lw-muted-2': '#d5e8ea',
      '--lw-accent': '#b9f0ff',
      '--lw-accent-2': '#f3d77b',
      '--lw-danger': '#ffc3b5',
      '--lw-danger-border': '#8e5248',
      '--lw-reader-shell': '#dce5dd',
      '--lw-reader-page': '#ffffeb',
      '--lw-shadow': 'rgba(0, 0, 0, 0.40)',
      '--lw-hero-glow': 'rgba(135, 205, 224, 0.28)'
    },
    'vassagonian-ruby': {
      '--lw-bg': '#170f12',
      '--lw-bg-soft': '#211418',
      '--lw-panel': '#2a181d',
      '--lw-panel-2': '#3a2227',
      '--lw-panel-3': '#4a2b31',
      '--lw-border': '#704146',
      '--lw-border-strong': '#9a6261',
      '--lw-text': '#f8ece4',
      '--lw-muted': '#d0a99e',
      '--lw-muted-2': '#efd4c7',
      '--lw-accent': '#ffcf6d',
      '--lw-accent-2': '#e27a67',
      '--lw-danger': '#ffb4a8',
      '--lw-danger-border': '#9b4b42',
      '--lw-reader-shell': '#dac8ad',
      '--lw-reader-page': '#fff4d9',
      '--lw-shadow': 'rgba(0, 0, 0, 0.42)',
      '--lw-hero-glow': 'rgba(193, 72, 67, 0.26)'
    },
    'wildlands-road': {
      '--lw-bg': '#10140f',
      '--lw-bg-soft': '#161d13',
      '--lw-panel': '#1d2718',
      '--lw-panel-2': '#27351f',
      '--lw-panel-3': '#344a2a',
      '--lw-border': '#536744',
      '--lw-border-strong': '#7c8b5f',
      '--lw-text': '#f1ecd8',
      '--lw-muted': '#bcc1a2',
      '--lw-muted-2': '#ddd7b8',
      '--lw-accent': '#e7d66f',
      '--lw-accent-2': '#98bf6e',
      '--lw-danger': '#ffc0a8',
      '--lw-danger-border': '#89513d',
      '--lw-reader-shell': '#d6d4ae',
      '--lw-reader-page': '#fff7da',
      '--lw-shadow': 'rgba(0, 0, 0, 0.36)',
      '--lw-hero-glow': 'rgba(105, 143, 82, 0.28)'
    },
    'darklord-iron': {
      '--lw-bg': '#0e0f10',
      '--lw-bg-soft': '#151617',
      '--lw-panel': '#1d1d1e',
      '--lw-panel-2': '#28292b',
      '--lw-panel-3': '#33363a',
      '--lw-border': '#55565a',
      '--lw-border-strong': '#7d7f84',
      '--lw-text': '#f1eee8',
      '--lw-muted': '#b9b9b9',
      '--lw-muted-2': '#dfdedb',
      '--lw-accent': '#ffcf68',
      '--lw-accent-2': '#c46f5b',
      '--lw-danger': '#ff9f91',
      '--lw-danger-border': '#91463e',
      '--lw-reader-shell': '#d0ccb7',
      '--lw-reader-page': '#fff8df',
      '--lw-shadow': 'rgba(0, 0, 0, 0.48)',
      '--lw-hero-glow': 'rgba(124, 127, 132, 0.24)'
    }
  };

  function localValue(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function readLocal() {
    return normalize({
      titleBanner: localValue(STORAGE_KEYS.titleBanner, defaults.titleBanner),
      coverArt: localValue(STORAGE_KEYS.coverArt, defaults.coverArt),
      theme: localValue(STORAGE_KEYS.theme, defaults.theme),
      readerStyleEnabled: localValue(STORAGE_KEYS.readerStyleEnabled, defaults.readerStyleEnabled),
      readerTheme: localValue(STORAGE_KEYS.readerTheme, defaults.readerTheme)
    });
  }

  function normalize(settings) {
    settings = { ...defaults, ...(settings || {}) };
    if (!titleBanners[settings.titleBanner]) settings.titleBanner = defaults.titleBanner;
    settings.coverArt = settings.coverArt === 'off' ? 'off' : 'on';
    if (!themes[settings.theme]) settings.theme = defaults.theme;
    settings.readerStyleEnabled = settings.readerStyleEnabled === 'on' ? 'on' : 'off';
    settings.readerTheme = settings.readerTheme || defaults.readerTheme;
    return settings;
  }

  function applyRoot(settings = readLocal()) {
    const clean = normalize(settings);
    const root = document.documentElement;
    Object.entries(themes[clean.theme]).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    root.dataset.lwTheme = clean.theme;
    root.dataset.lwCoverArt = clean.coverArt;
    root.dataset.lwReaderTheme = clean.readerTheme;
    root.classList.toggle('lw-cover-art-off', clean.coverArt === 'off');
    return clean;
  }

  function applyDocument(settings = readLocal()) {
    const clean = applyRoot(settings);
    if (document.body) {
      document.body.dataset.lwTheme = clean.theme;
      document.body.dataset.lwCoverArt = clean.coverArt;
      document.body.dataset.lwReaderTheme = clean.readerTheme;
      document.body.classList.toggle('lw-cover-art-off', clean.coverArt === 'off');
    }
    const banner = titleBanners[clean.titleBanner] || titleBanners[defaults.titleBanner];
    document.querySelectorAll('[data-lw-title-banner]').forEach((image) => {
      image.src = banner.path;
      image.alt = banner.name;
    });
    return clean;
  }

  function injectEarlyCss() {
    if (document.getElementById('lw-appearance-early-css')) return;
    const style = document.createElement('style');
    style.id = 'lw-appearance-early-css';
    style.textContent = `
      body {
        background: var(--lw-bg) !important;
        color: var(--lw-text) !important;
      }
      header, .toolbar, .tabs, .panel, .book, .book-link, .stat-card, .quick-card,
      .quick-tabs-divider, .item-row, .status-grid, .quick-panel, .top-dashboard,
      .layout-bar, .menu-popover, .death-option, .combat-meter-card,
      .cartwheel-game, .message, .file-mode-lock {
        background-color: var(--lw-panel) !important;
        border-color: var(--lw-border) !important;
        color: var(--lw-text) !important;
      }
      .status-grid, .quick-panel, .top-dashboard, #view, .app-pane {
        background-color: var(--lw-bg-soft) !important;
      }
      .reader-pane {
        background-color: var(--lw-reader-shell) !important;
        border-color: var(--lw-border-strong) !important;
      }
      #book-frame {
        background-color: var(--lw-reader-page) !important;
      }
      h1, h2, h3, .book strong, .book-link strong, .stat-card strong,
      .panel h2, .status-value, .card-collapsed-title {
        color: var(--lw-accent) !important;
      }
      a, a:visited {
        color: var(--lw-accent) !important;
      }
      button, .panel a, .top a, .actions a {
        border-color: var(--lw-border-strong) !important;
        background-color: var(--lw-panel-2) !important;
        color: var(--lw-accent) !important;
      }
      .app-menu-button,
      .card-collapse-button,
      .card-menu-button,
      .book-details-button {
        width: 20px !important;
        min-width: 20px !important;
        height: 20px !important;
        min-height: 20px !important;
        padding: 0 !important;
        display: grid !important;
        place-items: center !important;
        border: 0 !important;
        border-radius: 999px !important;
        background-color: color-mix(in srgb, var(--lw-muted-2) 14%, transparent) !important;
        color: var(--lw-muted-2) !important;
        font-size: 0 !important;
        line-height: 0 !important;
      }
      .app-menu-button:hover,
      .card-collapse-button:hover,
      .card-menu-button:hover,
      .book-details-button:hover {
        background-color: color-mix(in srgb, var(--lw-muted-2) 22%, transparent) !important;
        color: var(--lw-text) !important;
      }
      input, select {
        background-color: var(--lw-bg) !important;
        border-color: var(--lw-border-strong) !important;
        color: var(--lw-text) !important;
      }
      .subtitle, .reader-title, .muted, .quick-note, .quick-title, .mode-note,
      .menu-heading, .stat-card span, .book small, .book span, .book-link span {
        color: var(--lw-muted-2) !important;
      }
      .cover-frame {
        background-color: #050807 !important;
        border-color: #050807 !important;
      }
      .book img, .cover-fallback, #cliTerminalContainer {
        background-color: var(--lw-bg) !important;
        border-color: var(--lw-border) !important;
      }
      .cover-frame img {
        display: block !important;
        height: auto !important;
        padding: 0 !important;
        background-color: #050807 !important;
        border-color: #050807 !important;
      }
      .lw-cover-art-off .cover-frame,
      .lw-cover-art-off .book > img,
      .lw-cover-art-off .book > .cover-fallback {
        display: none !important;
      }
      .lw-cover-art-off .book {
        min-height: 0 !important;
        grid-template-rows: auto auto auto !important;
      }
    `;
    document.head.appendChild(style);
  }

  injectEarlyCss();
  applyRoot();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => applyDocument(), { once: true });
  } else {
    applyDocument();
  }

  window.LoneWolfReduxEarlyAppearance = {
    keys: STORAGE_KEYS,
    defaults,
    readLocal,
    applyRoot,
    applyDocument
  };
})();
