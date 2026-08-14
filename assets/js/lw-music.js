(() => {
  const SESSION_KEY = 'lonewolf_redux.music.session.v1';
  const MANIFEST_URL = 'assets/audio/music-manifest.json';
  const PLAYLIST_NAMES = Object.freeze({
    journey: 'Journey',
    'tavern-and-rest': 'Tavern and Rest',
    'ancient-mysteries': 'Ancient Mysteries',
    'dark-roads': 'Dark Roads',
    'all-approved-tracks': 'All Approved Tracks'
  });

  const state = {
    manifest: null,
    tracks: [],
    currentId: '',
    queue: [],
    queueIndex: 0,
    status: 'loading',
    error: '',
    restorePending: false,
    initialized: false
  };
  const audio = new Audio();
  audio.preload = 'metadata';

  function settingsApi() {
    return window.LoneWolfReduxSettings || null;
  }

  function preferences() {
    const api = settingsApi();
    return api ? api.normalize(api.readLocal()) : {
      musicEnabled: 'off', musicVolume: 0.35, musicPlaylist: 'journey', musicShuffle: 'off', musicRepeat: 'playlist'
    };
  }

  function trackById(id) {
    return state.tracks.find((track) => track.id === id) || null;
  }

  function currentTrack() {
    return trackById(state.currentId) || state.tracks[0] || null;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'\"]/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[character]));
  }

  function playlistTracks(playlist = preferences().musicPlaylist) {
    const matching = state.tracks.filter((track) => Array.isArray(track.playlists) && track.playlists.includes(playlist));
    return matching.length ? matching : state.tracks.slice();
  }

  function buildQueue(keepCurrent = true) {
    const prefs = preferences();
    const tracks = playlistTracks(prefs.musicPlaylist);
    let queue = tracks.map((track) => track.id);
    if (prefs.musicShuffle === 'on') {
      for (let i = queue.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [queue[i], queue[j]] = [queue[j], queue[i]];
      }
    }
    if (keepCurrent && state.currentId && queue.includes(state.currentId)) {
      queue = [state.currentId, ...queue.filter((id) => id !== state.currentId)];
    }
    state.queue = queue;
    state.queueIndex = Math.max(0, queue.indexOf(state.currentId));
    if (!state.currentId || !queue.includes(state.currentId)) state.currentId = queue[0] || '';
  }

  function saveSession() {
    const track = currentTrack();
    if (!track) return;
    const snapshot = {
      currentId: track.id,
      position: Number.isFinite(audio.currentTime) ? Math.max(0, audio.currentTime) : 0,
      queue: state.queue,
      queueIndex: state.queueIndex,
      wasPlaying: !audio.paused && !audio.ended,
      savedAt: Date.now()
    };
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(snapshot)); } catch {}
  }

  function loadSession() {
    try {
      const value = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch {
      return null;
    }
  }

  function emit() {
    syncControls();
    window.dispatchEvent(new CustomEvent('lonewolf-music-state', { detail: getState() }));
  }

  function setSource(track, position = 0) {
    if (!track) return;
    state.currentId = track.id;
    state.queueIndex = Math.max(0, state.queue.indexOf(track.id));
    if (audio.getAttribute('src') !== track.path) {
      audio.src = track.path;
      audio.load();
    }
    const applyPosition = () => {
      if (Number.isFinite(position) && position > 0) {
        try { audio.currentTime = position; } catch {}
      }
    };
    if (audio.readyState >= 1) applyPosition();
    else audio.addEventListener('loadedmetadata', applyPosition, { once: true });
    emit();
  }

  async function persistPreferences(patch) {
    const api = settingsApi();
    if (!api) return;
    await api.savePatch(patch);
  }

  async function requestPlay({ restore = false } = {}) {
    const track = currentTrack();
    if (!track) return;
    await persistPreferences({ musicEnabled: 'on' });
    audio.volume = preferences().musicVolume;
    if (audio.getAttribute('src') !== track.path) setSource(track, 0);
    try {
      await audio.play();
      state.status = 'playing';
      state.error = '';
      state.restorePending = false;
    } catch (error) {
      state.status = restore ? 'resume' : 'paused';
      state.error = restore ? 'Resume background music when ready.' : 'Playback is ready when you press Play.';
    }
    saveSession();
    emit();
  }

  function pause() {
    audio.pause();
    state.status = 'paused';
    state.restorePending = false;
    saveSession();
    emit();
  }

  function move(delta) {
    if (!state.queue.length) buildQueue();
    if (!state.queue.length) return;
    const wasPlaying = !audio.paused;
    let next = state.queueIndex + delta;
    if (next < 0) next = state.queue.length - 1;
    if (next >= state.queue.length) next = 0;
    state.queueIndex = next;
    setSource(trackById(state.queue[next]), 0);
    if (wasPlaying) requestPlay();
    else { saveSession(); emit(); }
  }

  function advance() {
    const prefs = preferences();
    if (prefs.musicRepeat === 'track') {
      audio.currentTime = 0;
      requestPlay();
      return;
    }
    if (!state.queue.length) buildQueue();
    const nextIndex = state.queueIndex + 1;
    if (nextIndex < state.queue.length) {
      state.queueIndex = nextIndex;
      setSource(trackById(state.queue[nextIndex]), 0);
      requestPlay();
      return;
    }
    if (prefs.musicRepeat === 'playlist') {
      buildQueue(false);
      state.queueIndex = 0;
      setSource(trackById(state.queue[0]), 0);
      requestPlay();
      return;
    }
    state.status = 'paused';
    saveSession();
    emit();
  }

  async function setVolume(value) {
    const volume = Math.min(1, Math.max(0, Number(value) || 0));
    audio.volume = volume;
    await persistPreferences({ musicVolume: volume });
    emit();
  }

  async function changeQueue(patch, keepCurrent = true) {
    const wasPlaying = !audio.paused;
    await persistPreferences(patch);
    buildQueue(keepCurrent);
    const track = currentTrack();
    if (track) setSource(track, 0);
    if (wasPlaying) await requestPlay();
    else { saveSession(); emit(); }
  }

  async function setPlaylist(playlist) {
    await changeQueue({ musicPlaylist: playlist }, false);
  }

  async function setShuffle(enabled) {
    await changeQueue({ musicShuffle: enabled ? 'on' : 'off' });
  }

  async function setRepeat(repeat) {
    await persistPreferences({ musicRepeat: repeat });
    emit();
  }

  async function selectTrack(trackId) {
    const track = trackById(trackId);
    if (!track || !playlistTracks().some((entry) => entry.id === track.id)) return;
    const wasPlaying = !audio.paused;
    if (!state.queue.includes(track.id)) buildQueue(false);
    state.queueIndex = state.queue.indexOf(track.id);
    setSource(track, 0);
    if (wasPlaying) await requestPlay();
    else { saveSession(); emit(); }
  }

  function statusLabel() {
    if (state.status === 'loading') return 'Loading';
    if (state.status === 'playing') return 'Playing';
    if (state.status === 'resume') return 'Resume available';
    if (state.status === 'off') return 'Off';
    return 'Paused';
  }

  function getState() {
    const prefs = preferences();
    const track = currentTrack();
    return {
      ready: state.initialized,
      status: state.status,
      error: state.error,
      track,
      playlist: prefs.musicPlaylist,
      playlistName: PLAYLIST_NAMES[prefs.musicPlaylist] || 'Soundtrack',
      volume: prefs.musicVolume,
      playing: state.status === 'playing'
    };
  }

  function compactMarkup(context = 'campaign') {
    const player = getState();
    const title = escapeHtml(player.track?.title || 'Preparing soundtrack');
    const action = player.playing ? 'pause' : 'play';
    const actionLabel = player.playing ? 'Pause background music' : 'Play background music';
    const actionGlyph = player.playing ? '&#10074;&#10074;' : '&#9654;';
    return `
      <section class="lw-music-compact${context === 'reader' ? ' lw-ui-panel' : ''}" data-lw-music-player data-lw-music-context="${context}" aria-label="Background music">
        <div class="lw-music-compact__head"><span class="lw-eyebrow">Soundtrack</span><span class="lw-ui-status" data-lw-music-status>${statusLabel()}</span></div>
        <strong data-lw-music-title>${title}</strong>
        <small data-lw-music-playlist>${player.playlistName}</small>
        <div class="lw-music-compact__controls">
          <button class="lw-ui-button" type="button" data-lw-music-action="previous" aria-label="Previous track" title="Previous track">&lsaquo;</button>
          <button class="lw-ui-button lw-ui-button--primary" type="button" data-lw-music-action="${action}" aria-label="${actionLabel}" title="${actionLabel}" data-lw-music-toggle>${actionGlyph}</button>
          <button class="lw-ui-button" type="button" data-lw-music-action="next" aria-label="Next track" title="Next track">&rsaquo;</button>
          <label class="lw-music-compact__volume"><span class="visually-hidden">Music volume</span><input type="range" min="0" max="1" step="0.05" value="${player.volume}" data-lw-music-volume aria-label="Music volume"></label>
        </div>
        <span class="lw-music-compact__message" data-lw-music-message>${player.error || 'Optional background music.'}</span>
      </section>`;
  }

  function playerCardMarkup(context = 'campaign') {
    const player = getState();
    const track = player.track || {};
    const action = player.playing ? 'pause' : 'play';
    const actionLabel = player.playing ? 'Pause background music' : 'Play background music';
    const actionGlyph = player.playing ? '&#10074;&#10074;' : '&#9654;';
    const isTools = context === 'tools';
    const tracks = playlistTracks(player.playlist);
    const playlistOptions = Object.entries(PLAYLIST_NAMES).map(([id, name]) =>
      `<option value="${id}" ${player.playlist === id ? 'selected' : ''}>${escapeHtml(name)}</option>`).join('');
    const creditRows = state.tracks.map((entry) => `
      <li><strong>${escapeHtml(entry.title)}</strong> <span>by ${escapeHtml(entry.artist)}</span>
        <a href="${escapeHtml(entry.sourceUrl)}" target="_blank" rel="noopener">Source</a>
        <a href="${escapeHtml(entry.licenseUrl)}" target="_blank" rel="noopener">${escapeHtml(entry.license)}</a>
      </li>`).join('');
    return `
      <section class="lw-ui-panel lw-music-player-card${isTools ? ' lw-music-player-card--tools' : ''}" data-lw-music-player data-lw-music-context="${context}" aria-label="Background music player">
        <header class="lw-music-player-card__head">
          <div><p class="lw-eyebrow">Background music</p><h2>${isTools ? 'Soundtrack controls' : 'Player'}</h2></div>
          <span class="lw-ui-status" data-lw-music-status>${statusLabel()}</span>
        </header>
        <div class="lw-music-player-card__now">
          <strong data-lw-music-title>${escapeHtml(track.title || 'Preparing soundtrack')}</strong>
          <span data-lw-music-artist>${escapeHtml(track.artist || 'Lone Wolf soundtrack')}</span>
        </div>
        <div class="lw-music-player-card__controls">
          <button class="lw-ui-button" type="button" data-lw-music-action="previous" aria-label="Previous track" title="Previous track">&lsaquo;</button>
          <button class="lw-ui-button lw-ui-button--primary" type="button" data-lw-music-action="${action}" aria-label="${actionLabel}" title="${actionLabel}" data-lw-music-toggle>${actionGlyph}</button>
          <button class="lw-ui-button" type="button" data-lw-music-action="next" aria-label="Next track" title="Next track">&rsaquo;</button>
          <label class="lw-music-player-card__volume"><span>Volume</span><input type="range" min="0" max="1" step="0.05" value="${player.volume}" data-lw-music-volume aria-label="Music volume"></label>
        </div>
        <p class="lw-music-player-card__message" data-lw-music-message>${escapeHtml(player.error || 'Optional background music. You control when it starts.')}</p>
        ${isTools ? `
          <div class="lw-music-player-card__settings">
            <label>Playlist<select data-lw-music-playlist>${playlistOptions}</select></label>
            <label>Repeat<select data-lw-music-repeat><option value="playlist" ${preferences().musicRepeat === 'playlist' ? 'selected' : ''}>Repeat playlist</option><option value="track" ${preferences().musicRepeat === 'track' ? 'selected' : ''}>Repeat track</option><option value="off" ${preferences().musicRepeat === 'off' ? 'selected' : ''}>Stop after queue</option></select></label>
            <label class="lw-music-player-card__shuffle"><input type="checkbox" data-lw-music-shuffle ${preferences().musicShuffle === 'on' ? 'checked' : ''}><span>Shuffle this playlist</span></label>
          </div>
          <section class="lw-music-player-card__tracks" aria-label="${escapeHtml(player.playlistName)} tracks">
            <header><h3>${escapeHtml(player.playlistName)}</h3><span data-lw-music-track-count>${tracks.length} tracks</span></header>
            <div>${tracks.map((entry) => `<button class="lw-ui-button${entry.id === track.id ? ' is-current' : ''}" type="button" data-lw-music-track="${escapeHtml(entry.id)}"><span><strong>${escapeHtml(entry.title)}</strong><small>${escapeHtml(entry.artist)}</small></span><span>${entry.id === track.id ? 'Playing now' : 'Play track'}</span></button>`).join('')}</div>
          </section>
          <details class="lw-music-player-card__credits"><summary>Music credits and licenses</summary><p>All tracks are integrated optional background music. The application does not offer audio downloads or exports.</p><ul>${creditRows}</ul></details>
        ` : `<a class="lw-ui-button lw-music-player-card__more" href="assistant.html?surface=tools&tool=soundtrack&resume=1">Open soundtrack controls</a>`}
      </section>`;
  }

  function syncControls() {
    const player = getState();
    document.querySelectorAll('[data-lw-music-player]').forEach((root) => {
      const title = root.querySelector('[data-lw-music-title]');
      const playlist = root.querySelector('[data-lw-music-playlist]');
      const status = root.querySelector('[data-lw-music-status]');
      const message = root.querySelector('[data-lw-music-message]');
      const toggle = root.querySelector('[data-lw-music-toggle]');
      const volume = root.querySelector('[data-lw-music-volume]');
      const artist = root.querySelector('[data-lw-music-artist]');
      const playlistSelect = root.querySelector('select[data-lw-music-playlist]');
      const repeatSelect = root.querySelector('[data-lw-music-repeat]');
      const shuffle = root.querySelector('[data-lw-music-shuffle]');
      const trackCount = root.querySelector('[data-lw-music-track-count]');
      if (title) title.textContent = player.track?.title || 'Preparing soundtrack';
      if (playlist) playlist.textContent = player.playlistName;
      if (status) status.textContent = statusLabel();
      if (message) message.textContent = player.error || 'Optional background music.';
      if (artist) artist.textContent = player.track?.artist || 'Lone Wolf soundtrack';
      if (toggle) {
        toggle.dataset.lwMusicAction = player.playing ? 'pause' : 'play';
        toggle.setAttribute('aria-label', player.playing ? 'Pause background music' : 'Play background music');
        toggle.setAttribute('title', player.playing ? 'Pause background music' : 'Play background music');
        toggle.innerHTML = player.playing ? '&#10074;&#10074;' : '&#9654;';
      }
      if (volume) volume.value = String(player.volume);
      if (playlistSelect) playlistSelect.value = player.playlist;
      if (repeatSelect) repeatSelect.value = preferences().musicRepeat;
      if (shuffle) shuffle.checked = preferences().musicShuffle === 'on';
      if (trackCount) trackCount.textContent = `${playlistTracks(player.playlist).length} tracks`;
      root.querySelectorAll('[data-lw-music-track]').forEach((button) => {
        const current = button.dataset.lwMusicTrack === player.track?.id;
        button.classList.toggle('is-current', current);
        const stateText = button.lastElementChild;
        if (stateText) stateText.textContent = current ? 'Playing now' : 'Play track';
      });
    });
  }

  async function refreshPreferences() {
    const prefs = preferences();
    audio.volume = prefs.musicVolume;
    if (state.initialized && !playlistTracks(prefs.musicPlaylist).some((track) => track.id === state.currentId)) {
      buildQueue(false);
      setSource(currentTrack(), 0);
    }
    emit();
  }

  async function initialize() {
    if (state.initialized) return getState();
    try {
      const response = await fetch(MANIFEST_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error('The soundtrack manifest is unavailable.');
      state.manifest = await response.json();
      state.tracks = Array.isArray(state.manifest?.tracks) ? state.manifest.tracks : [];
      if (!state.tracks.length) throw new Error('The soundtrack does not contain any playable tracks.');
      const snapshot = loadSession();
      const prefs = preferences();
      state.currentId = trackById(snapshot?.currentId)?.id || playlistTracks(prefs.musicPlaylist)[0]?.id || state.tracks[0].id;
      state.queue = Array.isArray(snapshot?.queue) && snapshot.queue.every((id) => trackById(id))
        ? snapshot.queue : [];
      state.queueIndex = Number.isInteger(snapshot?.queueIndex) ? snapshot.queueIndex : 0;
      if (!state.queue.length || !state.queue.includes(state.currentId)) buildQueue();
      setSource(currentTrack(), Number(snapshot?.position) || 0);
      state.initialized = true;
      state.status = prefs.musicEnabled === 'on' ? 'paused' : 'off';
      state.restorePending = Boolean(snapshot?.wasPlaying && prefs.musicEnabled === 'on');
      emit();
      if (state.restorePending) requestPlay({ restore: true });
    } catch (error) {
      state.status = 'paused';
      state.error = error?.message || 'Background music is unavailable.';
      emit();
    }
    return getState();
  }

  audio.addEventListener('play', () => { state.status = 'playing'; state.error = ''; emit(); });
  audio.addEventListener('pause', () => {
    if (!audio.ended && state.status !== 'off') { state.status = 'paused'; saveSession(); emit(); }
  });
  audio.addEventListener('ended', advance);
  audio.addEventListener('error', () => { state.status = 'paused'; state.error = 'This track could not be played.'; emit(); });

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-lw-music-action]');
    if (!button) return;
    event.preventDefault();
    const action = button.dataset.lwMusicAction;
    if (action === 'play') requestPlay();
    else if (action === 'pause') pause();
    else if (action === 'previous') move(-1);
    else if (action === 'next') move(1);
  });
  document.addEventListener('input', (event) => {
    const input = event.target.closest('[data-lw-music-volume]');
    if (input) setVolume(input.value);
  });
  document.addEventListener('change', (event) => {
    const playlist = event.target.closest('[data-lw-music-playlist]');
    if (playlist && playlist.tagName === 'SELECT') setPlaylist(playlist.value);
    const repeat = event.target.closest('[data-lw-music-repeat]');
    if (repeat) setRepeat(repeat.value);
    const shuffle = event.target.closest('[data-lw-music-shuffle]');
    if (shuffle) setShuffle(shuffle.checked);
  });
  document.addEventListener('click', (event) => {
    const track = event.target.closest('[data-lw-music-track]');
    if (!track) return;
    event.preventDefault();
    selectTrack(track.dataset.lwMusicTrack);
  });
  window.addEventListener('beforeunload', saveSession);

  window.LoneWolfMusic = {
    initialize,
    compactMarkup,
    playerCardMarkup,
    getState,
    refreshPreferences,
    play: () => requestPlay(),
    pause,
    previous: () => move(-1),
    next: () => move(1),
    setVolume,
    setPlaylist,
    setShuffle,
    setRepeat,
    selectTrack
  };

  initialize();
})();
