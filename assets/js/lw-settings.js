(function () {
  const STORAGE_KEYS = {
    titleBanner: 'lonewolf_redux.appearance.titleBanner.v1',
    coverArt: 'lonewolf_redux.appearance.coverArt.v1',
    theme: 'lonewolf_redux.appearance.theme.v1',
    readerStyleEnabled: 'lonewolf_redux.reader.styleEnabled.v1',
    readerTheme: 'lonewolf_redux.reader.theme.v1'
  };

  const titleBanners = [
    { id: 'title1', name: 'Classic Title', path: 'assets/images/title-banners/title1.png' },
    { id: 'title2', name: 'Red Banner', path: 'assets/images/title-banners/title2.png' },
    { id: 'title3', name: 'Painted Banner', path: 'assets/images/title-banners/title3.png' }
  ];

  const themes = [
    {
      id: 'kai-gold',
      name: 'Classic Kai Gold',
      note: 'The first-start classic look.',
      vars: {
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
      }
    },
    {
      id: 'sommerswerd-dawn',
      name: 'Sommerswerd Dawn',
      note: 'Bright steel, sunrise gold, clean wins.',
      vars: {
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
      }
    },
    {
      id: 'durenor-sea',
      name: 'Durenor Sea',
      note: 'Harbour lamps and cold water.',
      vars: {
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
      }
    },
    {
      id: 'kalte-frost',
      name: 'Kalte Frost',
      note: 'Ice, breath, and bad decisions in mittens.',
      vars: {
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
      }
    },
    {
      id: 'vassagonian-ruby',
      name: 'Vassagonian Ruby',
      note: 'Court intrigue, red glass, sharp knives.',
      vars: {
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
      }
    },
    {
      id: 'wildlands-road',
      name: 'Wildlands Road',
      note: 'Mud, moss, and one more march.',
      vars: {
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
      }
    },
    {
      id: 'darklord-iron',
      name: 'Darklord Iron',
      note: 'For when the map gets mean.',
      vars: {
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
    }
  ];

  function readerBookCss({
    shell,
    page,
    panel,
    panelAlt,
    text,
    muted,
    accent,
    accentHover,
    border,
    header = '#050806',
    subtitle = '#8f1510',
    imageFilter = ''
  }) {
    return `
      html, body {
        background: ${shell} !important;
        color: ${text} !important;
      }
      body {
        text-rendering: optimizeLegibility;
      }
      .container {
        background: ${page} !important;
      }
      article,
      .maintext,
      .frontmatter,
      .numbered,
      .glossary {
        background: ${page} !important;
        color: ${text} !important;
      }
      article,
      article p,
      article li,
      article dd,
      article dt,
      article td,
      article th,
      article blockquote,
      article cite,
      article span,
      article div {
        color: ${text} !important;
      }
      article h2,
      article h3,
      article h4,
      article h5,
      article h6,
      .smallcaps {
        color: ${text} !important;
      }
      article figcaption,
      #license,
      #license p,
      caption {
        color: ${muted} !important;
      }
      a,
      a:visited,
      article a,
      article a:visited,
      #license a,
      #license a:visited {
        background-color: transparent !important;
        color: ${accent} !important;
        text-decoration-color: ${accent} !important;
      }
      a:hover,
      a:visited:hover,
      article a:hover,
      article a:visited:hover {
        background-color: ${accentHover} !important;
        color: ${accent} !important;
      }
      table,
      .table,
      .table-responsive,
      .maintext table,
      .maintext td,
      .maintext th {
        background: ${page} !important;
        color: ${text} !important;
        border-color: ${border} !important;
      }
      .maintext .random-number-table td,
      .maintext .combat-results-table th,
      .maintext .combat-results-table td,
      .maintext .action-chart th,
      .maintext .action-chart td {
        border-color: ${border} !important;
      }
      .maintext .random-number-table tr:nth-child(2n) td:nth-child(2n),
      .maintext .random-number-table tr:nth-child(2n+1) td:nth-child(2n+1),
      .maintext .combat-results-table tr:nth-child(2n) td,
      .maintext .action-chart tr:nth-child(2n) {
        background-color: ${panelAlt} !important;
      }
      .choice,
      .puzzle,
      .deadend,
      .combat,
      #footnotes {
        background: ${panel} !important;
        border-color: ${border} !important;
      }
      #main-header h1 {
        background: ${header} !important;
        color: ${text} !important;
      }
      #main-header h2 {
        background: ${subtitle} !important;
        color: ${text} !important;
        border-color: ${border} !important;
      }
      .navbar-dever,
      .navbar-dever li > a,
      .navbar-dever li > :link,
      .navbar-dever li > :visited {
        background: ${header} !important;
        color: ${text} !important;
      }
      .navbar-dever li > a:hover,
      .navbar-dever li > :link:hover,
      .navbar-dever li > :visited:hover {
        background: ${panelAlt} !important;
        color: ${accent} !important;
      }
      hr {
        border-color: ${border} !important;
      }
      img {
        ${imageFilter ? `filter: ${imageFilter};` : ''}
      }
    `;
  }

  const readerThemes = [
    { id: 'original', name: 'Original Project Aon', css: '' },
    {
      id: 'redux-dark',
      name: 'Redux Dark',
      css: readerBookCss({
        shell: '#080b08',
        page: '#141911',
        panel: '#1b2117',
        panelAlt: '#252d20',
        text: '#f3ecd6',
        muted: '#c5bea3',
        accent: '#f4d477',
        accentHover: '#2e2612',
        border: '#5f5633',
        header: '#050705',
        subtitle: '#8f1711',
        imageFilter: 'sepia(0.08) brightness(0.9) contrast(1.08)'
      })
    },
    {
      id: 'parchment',
      name: 'Warm Parchment',
      css: readerBookCss({
        shell: '#e3d6ad',
        page: '#fff4d5',
        panel: '#f4e5bd',
        panelAlt: '#ead8aa',
        text: '#2b2116',
        muted: '#6d5841',
        accent: '#a31d16',
        accentHover: '#f6d5c9',
        border: '#b89f6b',
        header: '#17110a',
        subtitle: '#bf2519'
      })
    },
    {
      id: 'wide-reading',
      name: 'Wide Reading',
      css: `
        ${readerBookCss({
          shell: '#ebe0bd',
          page: '#fff8dd',
          panel: '#f5e9c5',
          panelAlt: '#e8d8a7',
          text: '#221a12',
          muted: '#66513a',
          accent: '#b11d17',
          accentHover: '#f5d6cc',
          border: '#b8a779',
          header: '#12100d',
          subtitle: '#bd2419'
        })}
        body {
          max-width: 980px !important;
          margin-left: auto !important;
          margin-right: auto !important;
        }
        body,
        article p,
        article li,
        article td,
        article blockquote {
          line-height: 1.55 !important;
        }
      `
    },
    {
      id: 'high-contrast',
      name: 'High Contrast',
      css: readerBookCss({
        shell: '#000',
        page: '#000',
        panel: '#101010',
        panelAlt: '#202020',
        text: '#fff',
        muted: '#e5e5e5',
        accent: '#ffe66d',
        accentHover: '#302800',
        border: '#fff',
        header: '#000',
        subtitle: '#5c0000',
        imageFilter: 'contrast(1.18)'
      })
    }
  ];

  const defaults = {
    titleBanner: 'title1',
    coverArt: 'on',
    theme: 'kai-gold',
    readerStyleEnabled: 'off',
    readerTheme: 'original'
  };

  function byId(list, id, fallbackId) {
    return list.find((entry) => entry.id === id) || list.find((entry) => entry.id === fallbackId) || list[0];
  }

  function readLocal() {
    return {
      titleBanner: localStorage.getItem(STORAGE_KEYS.titleBanner) || defaults.titleBanner,
      coverArt: localStorage.getItem(STORAGE_KEYS.coverArt) || defaults.coverArt,
      theme: localStorage.getItem(STORAGE_KEYS.theme) || defaults.theme,
      readerStyleEnabled: localStorage.getItem(STORAGE_KEYS.readerStyleEnabled) || defaults.readerStyleEnabled,
      readerTheme: localStorage.getItem(STORAGE_KEYS.readerTheme) || defaults.readerTheme
    };
  }

  function settingsToValues(settings) {
    return {
      [STORAGE_KEYS.titleBanner]: settings.titleBanner,
      [STORAGE_KEYS.coverArt]: settings.coverArt,
      [STORAGE_KEYS.theme]: settings.theme,
      [STORAGE_KEYS.readerStyleEnabled]: settings.readerStyleEnabled,
      [STORAGE_KEYS.readerTheme]: settings.readerTheme
    };
  }

  function appearanceStorageKeys() {
    return Object.values(STORAGE_KEYS);
  }

  function valuesToSettings(values) {
    values = values && typeof values === 'object' ? values : {};
    return {
      titleBanner: values[STORAGE_KEYS.titleBanner] || defaults.titleBanner,
      coverArt: values[STORAGE_KEYS.coverArt] || defaults.coverArt,
      theme: values[STORAGE_KEYS.theme] || defaults.theme,
      readerStyleEnabled: values[STORAGE_KEYS.readerStyleEnabled] || defaults.readerStyleEnabled,
      readerTheme: values[STORAGE_KEYS.readerTheme] || defaults.readerTheme
    };
  }

  function normalize(settings) {
    settings = { ...defaults, ...(settings || {}) };
    settings.titleBanner = byId(titleBanners, settings.titleBanner, defaults.titleBanner).id;
    settings.coverArt = settings.coverArt === 'off' ? 'off' : 'on';
    settings.theme = byId(themes, settings.theme, defaults.theme).id;
    settings.readerStyleEnabled = settings.readerStyleEnabled === 'on' ? 'on' : 'off';
    settings.readerTheme = byId(readerThemes, settings.readerTheme, defaults.readerTheme).id;
    return settings;
  }

  function writeLocal(settings) {
    const clean = normalize(settings);
    localStorage.setItem(STORAGE_KEYS.titleBanner, clean.titleBanner);
    localStorage.setItem(STORAGE_KEYS.coverArt, clean.coverArt);
    localStorage.setItem(STORAGE_KEYS.theme, clean.theme);
    localStorage.setItem(STORAGE_KEYS.readerStyleEnabled, clean.readerStyleEnabled);
    localStorage.setItem(STORAGE_KEYS.readerTheme, clean.readerTheme);
    return clean;
  }

  function ensureRuntimeStyle(doc = document) {
    if (doc.getElementById('lw-settings-runtime-css')) return;
    const style = doc.createElement('style');
    style.id = 'lw-settings-runtime-css';
    style.textContent = `
      body {
        background: var(--lw-bg) !important;
        color: var(--lw-text) !important;
      }
      header {
        background-color: var(--lw-panel) !important;
        border-color: var(--lw-border-strong) !important;
      }
      header, .toolbar, .tabs, .panel, .book, .stat-card, .quick-card, .quick-tabs-divider, .item-row,
      .status-grid, .quick-panel, .top-dashboard, .layout-bar, .menu-popover,
      .death-option, .combat-meter-card, .cartwheel-game, .message, .file-mode-lock {
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
      .panel h2, h1, .book strong, .stat-card strong, .status-value,
      .card-collapsed-title, .combat-meter-ratio strong, .receipt-detail-row strong,
      .achievement-toast small {
        color: var(--lw-accent) !important;
      }
      a, a:visited {
        color: var(--lw-accent) !important;
      }
      .subtitle, .reader-title, .quick-stat-label, .choice-title, .section-subtitle,
      .receipt-summary, .value, .status-subvalue {
        color: var(--lw-muted-2) !important;
      }
      .muted, .quick-note, .quick-title, .mode-note, .menu-heading, .stat-card span,
      .book small, .book span, .combat-meter-meta, .combat-meter-note,
      .combat-meter-notes, .history-meta, .panel .muted {
        color: var(--lw-muted) !important;
      }
      button, .panel a, .top a {
        border-color: var(--lw-border-strong) !important;
        background-color: var(--lw-panel-2) !important;
        color: var(--lw-accent) !important;
      }
      button:hover, .panel a:hover, .top a:hover, .book:hover {
        border-color: var(--lw-accent-2) !important;
        background-color: var(--lw-panel-3) !important;
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
      button.active {
        background-color: var(--lw-accent) !important;
        border-color: var(--lw-accent) !important;
        color: var(--lw-bg) !important;
      }
      button.danger, .panel-danger {
        border-color: var(--lw-danger-border) !important;
        color: var(--lw-danger) !important;
      }
      input, select {
        background-color: var(--lw-bg) !important;
        border-color: var(--lw-border-strong) !important;
        color: var(--lw-text) !important;
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
      .achievement-toast {
        background-color: var(--lw-panel-2) !important;
        border-color: var(--lw-accent-2) !important;
      }
      .combat-meter-fill.meter-good { background: #65a35a !important; }
      .combat-meter-fill.meter-warning { background: var(--lw-accent-2) !important; }
      .combat-meter-fill.meter-danger { background: #b85a4c !important; }
      .lw-cover-art-off .cover-frame,
      .lw-cover-art-off .book > img,
      .lw-cover-art-off .book > .cover-fallback {
        display: none !important;
      }
      .lw-cover-art-off .book {
        min-height: 0 !important;
        grid-template-rows: auto auto auto !important;
      }
      .lw-cover-art-off .books {
        grid-template-columns: repeat(5, minmax(120px, 1fr)) !important;
      }
      .lw-cover-art-off .list .book {
        grid-template-columns: 1fr !important;
      }
      .settings-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.55rem;
      }
      .settings-option {
        min-height: 72px;
        padding: 0.55rem;
        display: grid;
        align-content: start;
        gap: 0.25rem;
        border: 1px solid var(--lw-border);
        border-radius: 6px;
        background: var(--lw-panel-2);
        color: var(--lw-text);
        text-align: left;
      }
      .settings-option.active {
        border-color: var(--lw-accent);
        background: var(--lw-accent);
        color: var(--lw-bg);
        box-shadow: 0 0 0 1px var(--lw-accent);
      }
      .settings-option.active strong,
      .settings-option.active small {
        color: var(--lw-bg);
      }
      .settings-option strong {
        color: var(--lw-accent);
      }
      .settings-option small {
        color: var(--lw-muted);
      }
      .banner-option img {
        width: 100%;
        max-height: 70px;
        object-fit: contain;
        background: rgba(0, 0, 0, 0.20);
      }
      .slot-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto auto auto;
        gap: 0.4rem;
        align-items: center;
      }
      .slot-row + .slot-row {
        margin-top: 0.4rem;
      }
      .settings-modal {
        position: fixed;
        inset: 0;
        display: grid;
        place-items: center;
        padding: 24px;
        background: rgba(0, 0, 0, 0.58);
        z-index: 100;
      }
      .settings-modal[hidden] {
        display: none;
      }
      .settings-dialog {
        width: min(880px, 100%);
        max-height: min(84vh, 760px);
        overflow: auto;
        padding: 18px;
        border: 1px solid var(--lw-border-strong);
        border-radius: 8px;
        background: var(--lw-panel);
        box-shadow: 0 18px 48px var(--lw-shadow);
      }
      .settings-dialog h2, .settings-dialog h3 {
        color: var(--lw-accent);
      }
      .settings-dialog h2 {
        margin: 0 0 0.65rem;
      }
      .settings-dialog h3 {
        margin: 1rem 0 0.45rem;
      }
      .settings-dialog .controls {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        flex-wrap: wrap;
        margin-top: 0.65rem;
      }
      @media (max-width: 620px) {
        .slot-row {
          grid-template-columns: 1fr;
        }
      }
    `;
    doc.head.appendChild(style);
  }

  function selectedTheme(settings = readLocal()) {
    return byId(themes, normalize(settings).theme, defaults.theme);
  }

  function themeVars(settings = readLocal()) {
    return selectedTheme(settings).vars;
  }

  function applyTheme(settings) {
    const theme = selectedTheme(settings);
    Object.entries(theme.vars).forEach(([key, value]) => {
      document.documentElement.style.setProperty(key, value);
    });
    document.documentElement.dataset.lwTheme = theme.id;
    document.body.dataset.lwTheme = theme.id;
  }

  function apply(settings = readLocal()) {
    const clean = normalize(settings);
    ensureRuntimeStyle();
    applyTheme(clean);
    document.documentElement.classList.toggle('lw-cover-art-off', clean.coverArt === 'off');
    document.documentElement.dataset.lwCoverArt = clean.coverArt;
    document.documentElement.dataset.lwReaderTheme = clean.readerTheme;
    document.body.classList.toggle('lw-cover-art-off', clean.coverArt === 'off');
    document.body.dataset.lwCoverArt = clean.coverArt;
    document.body.dataset.lwReaderTheme = clean.readerTheme;
    document.querySelectorAll('[data-lw-title-banner]').forEach((image) => {
      const banner = byId(titleBanners, clean.titleBanner, defaults.titleBanner);
      image.src = banner.path;
      image.alt = banner.name;
    });
    return clean;
  }

  async function fetchRemotePreferences() {
    if (window.location.protocol === 'file:') return { version: 1, values: {} };
    try {
      const response = await fetch('/api/ui-preferences', { cache: 'no-store' });
      if (!response.ok) return { version: 1, values: {} };
      return await response.json();
    } catch {
      return { version: 1, values: {} };
    }
  }

  async function syncFromRemote() {
    const remote = await fetchRemotePreferences();
    const values = remote?.values && typeof remote.values === 'object' ? remote.values : {};
    Object.entries(STORAGE_KEYS).forEach(([, key]) => {
      if (values[key] !== undefined) {
        localStorage.setItem(key, String(values[key]));
      }
    });
    return apply(readLocal());
  }

  async function savePatch(patch) {
    const clean = writeLocal({ ...readLocal(), ...(patch || {}) });
    apply(clean);
    window.dispatchEvent(new CustomEvent('lonewolf-settings-changed', { detail: clean }));
    if (window.location.protocol === 'file:') return clean;
    const remote = await fetchRemotePreferences();
    const values = remote?.values && typeof remote.values === 'object' ? { ...remote.values } : {};
    Object.assign(values, settingsToValues(clean));
    try {
      await fetch('/api/ui-preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: 1, values })
      });
    } catch {}
    return clean;
  }

  function readerCss(settings = readLocal()) {
    const clean = normalize(settings);
    if (clean.readerStyleEnabled !== 'on') return '';
    const readerTheme = byId(readerThemes, clean.readerTheme, defaults.readerTheme);
    if (readerTheme.id === 'redux-dark') {
      const vars = themeVars(clean);
      return readerBookCss({
        shell: vars['--lw-bg-soft'],
        page: vars['--lw-bg'],
        panel: vars['--lw-panel'],
        panelAlt: vars['--lw-panel-2'],
        text: vars['--lw-text'],
        muted: vars['--lw-muted-2'],
        accent: vars['--lw-accent'],
        accentHover: vars['--lw-panel-3'],
        border: vars['--lw-border-strong'],
        header: '#050705',
        subtitle: '#8f1711',
        imageFilter: 'sepia(0.08) brightness(0.9) contrast(1.08)'
      });
    }
    return readerTheme.css || '';
  }

  function injectReaderTheme(frame, settings = readLocal()) {
    try {
      const doc = frame?.contentDocument;
      if (!doc) return;
      const existing = doc.getElementById('lw-reader-theme-css');
      if (existing) existing.remove();
      const css = readerCss(settings);
      if (!css) return;
      const style = doc.createElement('style');
      style.id = 'lw-reader-theme-css';
      style.textContent = css;
      doc.head.appendChild(style);
    } catch {}
  }

  window.LoneWolfReduxSettings = {
    keys: STORAGE_KEYS,
    defaults,
    titleBanners,
    themes,
    readerThemes,
    readLocal,
    writeLocal,
    normalize,
    appearanceStorageKeys,
    selectedTheme,
    themeVars,
    apply,
    syncFromRemote,
    savePatch,
    settingsToValues,
    valuesToSettings,
    readerCss,
    injectReaderTheme
  };
})();
