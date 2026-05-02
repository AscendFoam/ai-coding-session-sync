const FIXTURE_SCENARIOS = {
  clean: {
    label: "Clean",
    detailFixture: "sample-session-detail-codex.json",
    selectedSessionKey: "codex:transcript:session-sample-001",
  },
  dirty: {
    label: "Dirty",
    detailFixture: "sample-session-detail-claude.json",
    selectedSessionKey: "claude:transcript:session-sample-claude-002",
  },
  conflict: {
    label: "Conflict",
    detailFixture: "sample-session-detail-conflict.json",
    selectedSessionKey: "codex:transcript:session-sample-conflict-001",
  },
};

const DETAIL_TABS = {
  manifest: {
    title: "Snapshot Detail",
    description: "Snapshot identity, export metadata, provider profile, and redaction warnings for the selected session.",
  },
  patch: {
    title: "Patch Guidance",
    description: "Patch replay state, recommended apply mode, and recovery guidance for safely resuming unfinished work.",
  },
  compare: {
    title: "Selected Window vs Full Timeline",
    description: "How the adapter trimmed local transcript history into the selected excerpt window that powers handoff/export.",
  },
  handoff: {
    title: "Operator Narrative",
    description: "The portable markdown handoff that a human or another coding agent can pick up on a different machine.",
  },
};

const HISTORY_STORAGE_KEY = "aiss.desktop.command-history";
const HISTORY_ENTRY_LIMIT = 80;

const COMMANDS = {
  open_palette: {
    label: "Open command palette",
    description: "Browse desktop actions from a single place.",
    group: "General",
    shortcut: "Ctrl/Cmd+K",
    keywords: ["palette", "commands", "menu"],
  },
  reload_data: {
    label: "Reload current source",
    description: "Refresh the current fixture or live API payload.",
    group: "General",
    shortcut: "R",
    keywords: ["reload", "refresh", "source"],
  },
  rescan_catalog: {
    label: "Rescan local session catalogs",
    description: "Trigger the live API rescan endpoint for Codex and Claude.",
    group: "Sync",
    shortcut: "Shift+R",
    keywords: ["rescan", "catalog", "live"],
  },
  open_live_api: {
    label: "Open live API bundle",
    description: "Open the current /api/ui-bundle payload in a new tab.",
    group: "Sync",
    shortcut: "O",
    keywords: ["open", "api", "bundle", "json"],
  },
  copy_session_key: {
    label: "Copy selected session key",
    description: "Copy the active session identifier for debugging or handoff.",
    group: "Session",
    shortcut: "Y",
    keywords: ["copy", "session", "clipboard"],
  },
  switch_to_fixtures: {
    label: "Switch to fixture mode",
    description: "Swap the workbench to synthetic desktop fixtures.",
    group: "General",
    keywords: ["fixture", "mode", "demo"],
  },
  switch_to_live: {
    label: "Switch to live API mode",
    description: "Swap the workbench to a live local API server.",
    group: "General",
    keywords: ["live", "api", "mode"],
  },
  focus_patch_tab: {
    label: "Focus patch guidance",
    description: "Jump the detail column to the patch replay tab.",
    group: "Detail",
    shortcut: "P",
    keywords: ["patch", "replay", "detail"],
  },
  focus_compare_tab: {
    label: "Focus excerpt compare",
    description: "Jump the detail column to the selected-vs-all excerpts tab.",
    group: "Detail",
    shortcut: "E",
    keywords: ["excerpt", "compare", "timeline"],
  },
  focus_handoff_tab: {
    label: "Focus handoff markdown",
    description: "Jump the detail column to the handoff tab.",
    group: "Detail",
    shortcut: "H",
    keywords: ["handoff", "markdown", "resume"],
  },
  focus_recommended_session: {
    label: "Open recommended project session",
    description: "Select the recommended session for the active project when available.",
    group: "Session",
    keywords: ["recommended", "project", "session"],
  },
  clear_filters: {
    label: "Clear tool, status, and search filters",
    description: "Reset the workbench filters to the broadest view.",
    group: "General",
    keywords: ["clear", "filters", "reset"],
  },
  clear_activity_log: {
    label: "Clear activity log",
    description: "Forget recent command history from this browser session.",
    group: "History",
    keywords: ["clear", "activity", "log"],
  },
  export_activity_log: {
    label: "Export command history",
    description: "Download the current browser session audit trail as JSON.",
    group: "History",
    keywords: ["export", "history", "audit", "json"],
  },
};

const state = {
  sourceMode: "fixtures",
  fixtureScenario: "clean",
  liveApiBase: "http://127.0.0.1:8765",
  tool: "all",
  status: "",
  q: "",
  detailTab: "manifest",
  commandPaletteOpen: false,
  commandQuery: "",
  commandActiveIndex: 0,
  activityLog: [],
  historyFilter: "all",
  historyGroupBy: "category",
  historySortOrder: "desc",
  historySessionId: null,
  historySessionStartedAt: null,
  historySequence: 0,
  bundle: null,
  selectedSessionKey: null,
  selectedProjectId: null,
  actionFeedback: null,
  loading: false,
  error: null,
};

const elements = {
  sourceFixtures: document.getElementById("sourceFixtures"),
  sourceLive: document.getElementById("sourceLive"),
  fixtureClean: document.getElementById("fixtureClean"),
  fixtureDirty: document.getElementById("fixtureDirty"),
  fixtureConflict: document.getElementById("fixtureConflict"),
  refreshButton: document.getElementById("refreshButton"),
  commandPaletteButton: document.getElementById("commandPaletteButton"),
  rescanButton: document.getElementById("rescanButton"),
  openApiButton: document.getElementById("openApiButton"),
  copySessionKeyButton: document.getElementById("copySessionKeyButton"),
  exportHistoryButton: document.getElementById("exportHistoryButton"),
  clearActivityLogButton: document.getElementById("clearActivityLogButton"),
  historyFilterAll: document.getElementById("historyFilterAll"),
  historyFilterWarn: document.getElementById("historyFilterWarn"),
  historyFilterSync: document.getElementById("historyFilterSync"),
  historyFilterDetail: document.getElementById("historyFilterDetail"),
  historyGroupSource: document.getElementById("historyGroupSource"),
  historyGroupCategory: document.getElementById("historyGroupCategory"),
  historyGroupFlat: document.getElementById("historyGroupFlat"),
  historySortDesc: document.getElementById("historySortDesc"),
  historySortAsc: document.getElementById("historySortAsc"),
  liveApiBase: document.getElementById("liveApiBase"),
  toolFilter: document.getElementById("toolFilter"),
  statusFilter: document.getElementById("statusFilter"),
  searchInput: document.getElementById("searchInput"),
  connectionMeta: document.getElementById("connectionMeta"),
  connectionSignals: document.getElementById("connectionSignals"),
  connectionPanel: document.getElementById("connectionPanel"),
  actionFeedback: document.getElementById("actionFeedback"),
  activityLog: document.getElementById("activityLog"),
  workspaceBanner: document.getElementById("workspaceBanner"),
  librarySurface: document.getElementById("librarySurface"),
  libraryMeta: document.getElementById("libraryMeta"),
  librarySummary: document.getElementById("librarySummary"),
  sessionList: document.getElementById("sessionList"),
  projectSurface: document.getElementById("projectSurface"),
  projectTitle: document.getElementById("projectTitle"),
  projectMeta: document.getElementById("projectMeta"),
  projectBadges: document.getElementById("projectBadges"),
  projectBanner: document.getElementById("projectBanner"),
  projectSummary: document.getElementById("projectSummary"),
  projectSignals: document.getElementById("projectSignals"),
  projectContexts: document.getElementById("projectContexts"),
  projectSessionList: document.getElementById("projectSessionList"),
  projectList: document.getElementById("projectList"),
  detailSurface: document.getElementById("detailSurface"),
  detailTitle: document.getElementById("detailTitle"),
  detailMeta: document.getElementById("detailMeta"),
  detailBadges: document.getElementById("detailBadges"),
  detailBanner: document.getElementById("detailBanner"),
  detailSummary: document.getElementById("detailSummary"),
  detailTabTitle: document.getElementById("detailTabTitle"),
  detailTabDescription: document.getElementById("detailTabDescription"),
  detailTabManifest: document.getElementById("detailTabManifest"),
  detailTabPatch: document.getElementById("detailTabPatch"),
  detailTabCompare: document.getElementById("detailTabCompare"),
  detailTabHandoff: document.getElementById("detailTabHandoff"),
  detailPanelManifest: document.getElementById("detailPanelManifest"),
  detailPanelPatch: document.getElementById("detailPanelPatch"),
  detailPanelCompare: document.getElementById("detailPanelCompare"),
  detailPanelHandoff: document.getElementById("detailPanelHandoff"),
  manifestPanel: document.getElementById("manifestPanel"),
  patchReplayPanel: document.getElementById("patchReplayPanel"),
  selectedExcerpts: document.getElementById("selectedExcerpts"),
  allExcerpts: document.getElementById("allExcerpts"),
  handoffPanel: document.getElementById("handoffPanel"),
  commandPaletteOverlay: document.getElementById("commandPaletteOverlay"),
  closeCommandPaletteButton: document.getElementById("closeCommandPaletteButton"),
  commandSearchInput: document.getElementById("commandSearchInput"),
  commandPaletteMeta: document.getElementById("commandPaletteMeta"),
  commandPaletteList: document.getElementById("commandPaletteList"),
};

init();

function init() {
  hydrateHistory();
  bindControls();
  hydrateFromUrl();
  syncControls();
  loadData();
}

function bindControls() {
  elements.sourceFixtures.addEventListener("click", () => {
    state.sourceMode = "fixtures";
    syncControls();
    loadData();
  });
  elements.sourceLive.addEventListener("click", () => {
    state.sourceMode = "live";
    syncControls();
    loadData();
  });
  elements.fixtureClean.addEventListener("click", () => {
    state.fixtureScenario = "clean";
    syncControls();
    loadData();
  });
  elements.fixtureDirty.addEventListener("click", () => {
    state.fixtureScenario = "dirty";
    syncControls();
    loadData();
  });
  elements.fixtureConflict.addEventListener("click", () => {
    state.fixtureScenario = "conflict";
    syncControls();
    loadData();
  });
  elements.refreshButton.addEventListener("click", () => loadData());
  elements.commandPaletteButton.addEventListener("click", () => executeCommand("open_palette", { source: "toolbar" }));
  elements.rescanButton.addEventListener("click", () => executeCommand("rescan_catalog", { source: "toolbar" }));
  elements.openApiButton.addEventListener("click", () => executeCommand("open_live_api", { source: "toolbar" }));
  elements.copySessionKeyButton.addEventListener("click", () => executeCommand("copy_session_key", { source: "toolbar" }));
  elements.exportHistoryButton.addEventListener("click", () => executeCommand("export_activity_log", { source: "toolbar" }));
  elements.clearActivityLogButton.addEventListener("click", () => executeCommand("clear_activity_log", { source: "toolbar" }));
  elements.historyFilterAll.addEventListener("click", () => setHistoryFilter("all"));
  elements.historyFilterWarn.addEventListener("click", () => setHistoryFilter("warn"));
  elements.historyFilterSync.addEventListener("click", () => setHistoryFilter("sync"));
  elements.historyFilterDetail.addEventListener("click", () => setHistoryFilter("detail"));
  elements.historyGroupSource.addEventListener("click", () => setHistoryGroupBy("source"));
  elements.historyGroupCategory.addEventListener("click", () => setHistoryGroupBy("category"));
  elements.historyGroupFlat.addEventListener("click", () => setHistoryGroupBy("flat"));
  elements.historySortDesc.addEventListener("click", () => setHistorySortOrder("desc"));
  elements.historySortAsc.addEventListener("click", () => setHistorySortOrder("asc"));
  elements.liveApiBase.addEventListener("change", () => {
    state.liveApiBase = elements.liveApiBase.value.trim() || "http://127.0.0.1:8765";
    syncUrl();
    if (state.sourceMode === "live") {
      loadData();
    }
  });
  elements.toolFilter.addEventListener("change", () => {
    state.tool = elements.toolFilter.value;
    if (state.sourceMode === "live") {
      loadData();
      return;
    }
    syncUrl();
    render();
  });
  elements.statusFilter.addEventListener("change", () => {
    state.status = elements.statusFilter.value;
    if (state.sourceMode === "live") {
      loadData();
      return;
    }
    syncUrl();
    render();
  });
  elements.searchInput.addEventListener("change", () => {
    state.q = elements.searchInput.value.trim();
    if (state.sourceMode === "live") {
      loadData();
      return;
    }
    syncUrl();
    render();
  });
  elements.detailTabManifest.addEventListener("click", () => setDetailTab("manifest"));
  elements.detailTabPatch.addEventListener("click", () => setDetailTab("patch"));
  elements.detailTabCompare.addEventListener("click", () => setDetailTab("compare"));
  elements.detailTabHandoff.addEventListener("click", () => setDetailTab("handoff"));
  elements.closeCommandPaletteButton.addEventListener("click", () => closeCommandPalette());
  elements.commandPaletteOverlay.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.dataset.closePalette === "true") {
      closeCommandPalette();
    }
    const commandId = target.closest("[data-command-id]")?.getAttribute("data-command-id");
    if (commandId) {
      executeCommand(commandId, { source: "palette" });
    }
    const bannerCommandId = target.closest("[data-banner-command]")?.getAttribute("data-banner-command");
    if (bannerCommandId) {
      executeCommand(bannerCommandId, { source: "banner" });
    }
  });
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const bannerCommandId = target.closest("[data-banner-command]")?.getAttribute("data-banner-command");
    if (bannerCommandId) {
      executeCommand(bannerCommandId, { source: "banner" });
    }
  });
  elements.commandSearchInput.addEventListener("input", () => {
    state.commandQuery = elements.commandSearchInput.value.trim();
    state.commandActiveIndex = 0;
    renderCommandPalette();
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (state.commandPaletteOpen) {
        closeCommandPalette();
      } else {
        openCommandPalette();
      }
    }
    if (event.key === "Escape" && state.commandPaletteOpen) {
      event.preventDefault();
      closeCommandPalette();
      return;
    }
    if (state.commandPaletteOpen && event.key === "ArrowDown") {
      event.preventDefault();
      moveCommandSelection(1);
      return;
    }
    if (state.commandPaletteOpen && event.key === "ArrowUp") {
      event.preventDefault();
      moveCommandSelection(-1);
      return;
    }
    if (state.commandPaletteOpen && event.key === "PageDown") {
      event.preventDefault();
      jumpCommandGroup(1);
      return;
    }
    if (state.commandPaletteOpen && event.key === "PageUp") {
      event.preventDefault();
      jumpCommandGroup(-1);
      return;
    }
    if (state.commandPaletteOpen && event.key === "Enter") {
      event.preventDefault();
      activateSelectedCommand();
      return;
    }
    if (event.repeat || event.isComposing) {
      return;
    }
    if (isEditableTarget(event.target)) {
      return;
    }
    const shortcutCommandId = findCommandShortcutMatch(event);
    if (shortcutCommandId) {
      event.preventDefault();
      executeCommand(shortcutCommandId, {
        source: "shortcut",
        closePalette: state.commandPaletteOpen,
      });
    }
  });
}

async function loadData() {
  state.loading = true;
  state.error = null;
  renderConnectionPanel();
  renderLoadingState();
  try {
    state.bundle = state.sourceMode === "fixtures" ? await loadFixtureBundle() : await loadLiveBundle();
    alignSelectedState();
    syncUrl();
    render();
  } catch (error) {
    console.error(error);
    state.error = error;
    state.bundle = null;
    render();
  } finally {
    state.loading = false;
    renderConnectionPanel();
  }
}

async function loadFixtureBundle() {
  const scenario = FIXTURE_SCENARIOS[state.fixtureScenario];
  const base = normalizeBase(state.liveApiBase);
  const [baseBundleFixture, codexDetailFixture, claudeDetailFixture, conflictDetailFixture, scenarioDetailFixture] =
    await Promise.all([
      fetchFixture(base, "sample-desktop-ui-bundle.json"),
      fetchFixture(base, "sample-session-detail-codex.json"),
      fetchFixture(base, "sample-session-detail-claude.json"),
      fetchFixture(base, "sample-session-detail-conflict.json"),
      fetchFixture(base, scenario.detailFixture),
    ]);

  const bundle = structuredClone(baseBundleFixture.payload);
  const detailsByKey = {
    [codexDetailFixture.payload.session.session_key]: codexDetailFixture.payload,
    [claudeDetailFixture.payload.session.session_key]: claudeDetailFixture.payload,
    [conflictDetailFixture.payload.session.session_key]: conflictDetailFixture.payload,
  };
  bundle.selected_session_detail = scenarioDetailFixture.payload;
  bundle.view_state = {
    ...bundle.view_state,
    selected_session_key:
      state.selectedSessionKey ||
      scenario.selectedSessionKey ||
      scenarioDetailFixture.payload.session?.session_key ||
      bundle.view_state?.selected_session_key ||
      null,
    selected_project_id:
      state.selectedProjectId ||
      scenarioDetailFixture.payload.session?.project_id ||
      bundle.project_catalog?.selected_project?.project_id ||
      bundle.view_state?.selected_project_id ||
      null,
    data_mode: "fixture",
  };
  bundle._fixtureDetails = detailsByKey;
  return buildBundleViewModel(bundle, {
    dataMode: "fixture",
    selectedSessionKey: bundle.view_state.selected_session_key,
    selectedProjectId: bundle.view_state.selected_project_id,
  });
}

async function loadLiveBundle() {
  const base = normalizeBase(state.liveApiBase);
  const params = new URLSearchParams();
  params.set("tool", state.tool);
  if (state.status) {
    params.set("status", state.status);
  }
  if (state.q) {
    params.set("q", state.q);
  }
  if (state.selectedSessionKey) {
    params.set("selected_session_key", state.selectedSessionKey);
  }
  if (state.selectedProjectId) {
    params.set("selected_project_id", state.selectedProjectId);
  }
  params.set("active_view", "session-detail");
  params.set("data_mode", "live");

  try {
    const bundle = await fetchJson(`${base}/api/ui-bundle?${params.toString()}`);
    return buildBundleViewModel(bundle, {
      dataMode: "live",
      selectedSessionKey: state.selectedSessionKey || bundle.view_state?.selected_session_key || null,
      selectedProjectId: state.selectedProjectId || bundle.view_state?.selected_project_id || null,
    });
  } catch (error) {
    const query = new URLSearchParams();
    query.set("tool", state.tool);
    if (state.status) {
      query.set("status", state.status);
    }
    if (state.q) {
      query.set("q", state.q);
    }
    const [sessions, projects] = await Promise.all([
      fetchJson(`${base}/api/sessions?${query.toString()}`),
      fetchJson(`${base}/api/projects?${query.toString()}`),
    ]);
    const selectedSessionKey = state.selectedSessionKey || sessions.sessions?.[0]?.session_key || null;
    let detail = null;
    if (selectedSessionKey) {
      try {
        detail = await fetchJson(`${base}/api/sessions/${encodeURIComponent(selectedSessionKey)}`);
      } catch (detailError) {
        console.warn(detailError);
      }
    }
    const selectedProjectId =
      state.selectedProjectId ||
      detail?.session?.project_id ||
      projects.projects?.[0]?.project_id ||
      null;
    return buildBundleViewModel(
      {
        schema_version: sessions.schema_version,
        generated_at: sessions.generated_at,
        bundle_id: "live-fallback",
        session_catalog: sessions,
        project_catalog: {
          ...projects,
          selected_project:
            (projects.projects || []).find((item) => item.project_id === selectedProjectId) || projects.selected_project || null,
        },
        selected_session_detail: detail,
        view_state: {
          active_view: "session-detail",
          selected_session_key: selectedSessionKey,
          selected_project_id: selectedProjectId,
          data_mode: "live",
          filters: {
            tool: state.tool,
            project_id: null,
            status: state.status || null,
            q: state.q,
            sort: "updated_at",
            order: "desc",
          },
        },
      },
      {
        dataMode: "live",
        selectedSessionKey,
        selectedProjectId,
      }
    );
  }
}

function buildBundleViewModel(bundle, overrides = {}) {
  const sessions = [...(bundle.session_catalog?.sessions || [])];
  const sessionMap = new Map(sessions.map((session) => [session.session_key, session]));
  const projects = [...(bundle.project_catalog?.projects || [])];
  const projectMap = new Map(projects.map((project) => [project.project_id, project]));
  const detailsByKey = {};

  if (bundle.selected_session_detail?.session?.session_key) {
    detailsByKey[bundle.selected_session_detail.session.session_key] = bundle.selected_session_detail;
  }
  if (bundle._fixtureDetails) {
    Object.assign(detailsByKey, bundle._fixtureDetails);
  }

  let selectedSessionKey =
    overrides.selectedSessionKey ||
    bundle.view_state?.selected_session_key ||
    bundle.selected_session_detail?.session?.session_key ||
    sessions[0]?.session_key ||
    null;

  if (selectedSessionKey && !sessionMap.has(selectedSessionKey) && !detailsByKey[selectedSessionKey]) {
    selectedSessionKey = sessions[0]?.session_key || null;
  }

  const selectedSessionSummary =
    (selectedSessionKey && sessionMap.get(selectedSessionKey)) ||
    bundle.selected_session_detail?.session ||
    null;

  let selectedProjectId =
    overrides.selectedProjectId ||
    bundle.view_state?.selected_project_id ||
    selectedSessionSummary?.project_id ||
    bundle.project_catalog?.selected_project?.project_id ||
    projects[0]?.project_id ||
    null;

  if (!selectedProjectId && selectedSessionSummary?.project_id) {
    selectedProjectId = selectedSessionSummary.project_id;
  }

  let selectedProject =
    (selectedProjectId && projectMap.get(selectedProjectId)) ||
    bundle.project_catalog?.selected_project ||
    null;

  if (!selectedProject && selectedSessionSummary?.project_id) {
    selectedProject = projectMap.get(selectedSessionSummary.project_id) || null;
  }
  if (!selectedProject && projects.length) {
    selectedProject = projects[0];
  }
  if (!selectedProjectId && selectedProject?.project_id) {
    selectedProjectId = selectedProject.project_id;
  }

  return {
    bundle,
    dataMode: overrides.dataMode || bundle.view_state?.data_mode || "fixture",
    sessions,
    projects,
    sessionMap,
    projectMap,
    detailsByKey,
    selectedSessionKey,
    selectedProjectId,
    selectedSessionSummary,
    selectedProject,
  };
}

function alignSelectedState() {
  if (!state.bundle) {
    state.selectedSessionKey = null;
    state.selectedProjectId = null;
    return;
  }
  state.selectedSessionKey = state.bundle.selectedSessionKey;
  state.selectedProjectId = state.bundle.selectedProjectId;
}

function render() {
  syncControls();
  renderConnectionPanel();

  if (state.error) {
    renderErrorState(state.error);
    return;
  }
  if (!state.bundle) {
    renderEmptyState("No data loaded.");
    return;
  }

  const model = state.bundle;
  const visibleSessions = filterSessions(model.sessions);
  const selection = coerceSelection(model, visibleSessions);

  renderLibraryMeta(visibleSessions, model);
  renderLibrarySummary(model);
  renderSessionList(visibleSessions);
  renderProjectView(selection.project, selection.detail, model);
  renderDetail(selection.detail);
  renderStateLayers(selection.project, selection.detail, visibleSessions, model);
  renderActionFeedback();
  renderActivityLog();
  renderCommandPalette();
  syncUrl();
}

function renderLoadingState() {
  elements.connectionMeta.textContent = "Loading…";
  elements.connectionSignals.innerHTML = badge("refreshing", "badge-neutral");
  setBanner(elements.workspaceBanner, {
    tone: "empty",
    title: "Refreshing desktop payload",
    copy: "The workbench is reloading session, project, and detail data from the active source.",
  });
  elements.libraryMeta.textContent = "Loading…";
  elements.librarySummary.innerHTML = renderMetricCard("Catalog", "Loading…", "Waiting for desktop bundle.");
  elements.sessionList.innerHTML = renderEmptyCard("Loading session catalog…");
  elements.projectTitle.textContent = "Loading…";
  elements.projectMeta.textContent = "Waiting for project detail…";
  elements.projectBadges.innerHTML = "";
  elements.projectSummary.innerHTML = renderMetricCard("Project", "Loading…", "Waiting for project summary.");
  elements.projectSignals.innerHTML = renderEmptyCard("Waiting for project signals…");
  elements.projectContexts.innerHTML = renderEmptyCard("Waiting for ranked contexts…");
  elements.projectSessionList.innerHTML = renderEmptyCard("Waiting for project sessions…");
  elements.projectList.innerHTML = renderEmptyCard("Loading project catalog…");
  elements.manifestPanel.innerHTML = renderEmptyCard("Waiting for snapshot detail…");
  elements.patchReplayPanel.innerHTML = renderEmptyCard("Waiting for patch guidance…");
  elements.selectedExcerpts.innerHTML = renderEmptyCard("Waiting for selected excerpts…");
  elements.allExcerpts.innerHTML = renderEmptyCard("Waiting for timeline…");
  elements.handoffPanel.textContent = "Loading handoff…";
  elements.detailTitle.textContent = "Loading…";
  elements.detailMeta.textContent = "Waiting for session detail…";
  elements.detailBadges.innerHTML = "";
  elements.detailSummary.innerHTML = renderMetricCard("Session", "Loading…", "Waiting for session detail.");
  clearSurfaceStates();
  setBanner(elements.projectBanner, null);
  setBanner(elements.detailBanner, null);
  renderActionFeedback();
  renderActivityLog();
  renderDetailTabs();
}

function renderErrorState(error) {
  const message = escapeHtml(error?.message || String(error));
  elements.connectionMeta.innerHTML = badge("Load failed", "badge-error");
  elements.connectionSignals.innerHTML = [
    badge(state.sourceMode === "live" ? "live path" : "fixture path", state.sourceMode === "live" ? "badge-mode-live" : "badge-mode-fixture"),
    badge("error", "badge-error"),
  ].join("");
  setBanner(elements.workspaceBanner, {
    tone: "error",
    title: "Desktop payload could not be loaded",
    copy: error?.message || String(error),
    actions: state.sourceMode === "live" ? ["Check live API base", "Try reload or switch to fixtures"] : ["Check fixture route", "Try reload or switch to live API"],
  });
  elements.libraryMeta.innerHTML = badge("Error", "badge-error");
  elements.librarySummary.innerHTML = renderMetricCard("Reason", message, "Check fixture path or live API base.");
  elements.sessionList.innerHTML = renderEmptyCard(`Could not load session catalog.\n\n${message}`);
  elements.projectTitle.textContent = "Load failed";
  elements.projectMeta.textContent = "Project data unavailable.";
  elements.projectBadges.innerHTML = badge("Error", "badge-error");
  elements.projectSummary.innerHTML = renderMetricCard("Reason", message, "Project catalog unavailable.");
  elements.projectSignals.innerHTML = renderEmptyCard("Project signals unavailable.");
  elements.projectContexts.innerHTML = renderEmptyCard("Ranked contexts unavailable.");
  elements.projectSessionList.innerHTML = renderEmptyCard("Project session list unavailable.");
  elements.projectList.innerHTML = renderEmptyCard("Project catalog unavailable.");
  elements.manifestPanel.innerHTML = renderEmptyCard("Snapshot detail unavailable.");
  elements.patchReplayPanel.innerHTML = renderEmptyCard("Patch guidance unavailable.");
  elements.selectedExcerpts.innerHTML = renderEmptyCard("Selected excerpt window unavailable.");
  elements.allExcerpts.innerHTML = renderEmptyCard("Timeline unavailable.");
  elements.handoffPanel.textContent = error?.message || String(error);
  elements.detailTitle.textContent = "Load failed";
  elements.detailMeta.textContent = "Session detail unavailable.";
  elements.detailBadges.innerHTML = badge("Error", "badge-error");
  elements.detailSummary.innerHTML = renderMetricCard("Reason", message, "Session detail unavailable.");
  clearSurfaceStates();
  setSurfaceState(elements.librarySurface, "error");
  setSurfaceState(elements.projectSurface, "error");
  setSurfaceState(elements.detailSurface, "error");
  setBanner(elements.projectBanner, {
    tone: "error",
    title: "Project view unavailable",
    copy: "Project-level signals could not be derived from the current data source.",
  });
  setBanner(elements.detailBanner, {
    tone: "error",
    title: "Session detail unavailable",
    copy: "Manifest, patch replay, compare data, and handoff content could not be loaded.",
  });
  renderActionFeedback();
  renderActivityLog();
  renderDetailTabs();
}

function renderEmptyState(message) {
  const safeMessage = escapeHtml(message);
  elements.connectionMeta.textContent = "";
  elements.connectionSignals.innerHTML = "";
  setBanner(elements.workspaceBanner, {
    tone: "empty",
    title: "No desktop data loaded",
    copy: message,
    actions: ["Try fixture mode", "Point live API base at a running local server"],
  });
  elements.libraryMeta.textContent = "";
  elements.librarySummary.innerHTML = renderMetricCard("Catalog", safeMessage, "No desktop data available yet.");
  elements.sessionList.innerHTML = renderEmptyCard(safeMessage);
  elements.projectTitle.textContent = "No project selected";
  elements.projectMeta.textContent = "Select a session or project to inspect repository state, latest pointers, and ranked local contexts.";
  elements.projectBadges.innerHTML = "";
  elements.projectSummary.innerHTML = renderMetricCard("Project", safeMessage, "Project detail will appear here.");
  elements.projectSignals.innerHTML = renderEmptyCard(safeMessage);
  elements.projectContexts.innerHTML = renderEmptyCard(safeMessage);
  elements.projectSessionList.innerHTML = renderEmptyCard(safeMessage);
  elements.projectList.innerHTML = renderEmptyCard(safeMessage);
  elements.handoffPanel.textContent = message;
  elements.manifestPanel.innerHTML = renderEmptyCard(safeMessage);
  elements.patchReplayPanel.innerHTML = renderEmptyCard(safeMessage);
  elements.selectedExcerpts.innerHTML = renderEmptyCard(safeMessage);
  elements.allExcerpts.innerHTML = renderEmptyCard(safeMessage);
  elements.detailTitle.textContent = "No session selected";
  elements.detailMeta.textContent = "Open one session to inspect snapshot detail, patch replay guidance, excerpt windows, and handoff markdown.";
  elements.detailBadges.innerHTML = "";
  elements.detailSummary.innerHTML = renderMetricCard("Session", safeMessage, "Session detail will appear here.");
  clearSurfaceStates();
  setSurfaceState(elements.librarySurface, "empty");
  setSurfaceState(elements.projectSurface, "empty");
  setSurfaceState(elements.detailSurface, "empty");
  setBanner(elements.projectBanner, {
    tone: "empty",
    title: "No project selected yet",
    copy: "Pick a session or project to populate repository state, latest pointers, and ranked context candidates.",
  });
  setBanner(elements.detailBanner, {
    tone: "empty",
    title: "No session detail selected yet",
    copy: "Manifest, patch guidance, excerpts, and handoff content will appear here once a session is selected.",
  });
  renderActionFeedback();
  renderActivityLog();
  renderDetailTabs();
}

function renderConnectionPanel() {
  const scenario = FIXTURE_SCENARIOS[state.fixtureScenario];
  const model = state.bundle;
  const bundle = model?.bundle;
  const summary = bundle?.session_catalog?.summary || {};
  const focusSession = model?.selectedSessionSummary;
  const focusProject = model?.selectedProject;

  if (state.loading) {
    elements.connectionMeta.textContent = "Refreshing current source…";
  } else if (state.sourceMode === "live") {
    elements.connectionMeta.textContent = "Live bundle over local desktop API";
  } else {
    elements.connectionMeta.textContent = `${scenario.label} fixture via /api/dev/fixture/*`;
  }

  elements.connectionSignals.innerHTML = [
    badge(state.sourceMode === "live" ? "live route" : scenario.label.toLowerCase(), state.sourceMode === "live" ? "badge-mode-live" : "badge-mode-fixture"),
    badge(state.tool === "all" ? "all tools" : state.tool, "badge-neutral"),
    badge(state.status || "all states", state.status ? statusBadgeClass(state.status) : "badge-neutral"),
    badge(state.loading ? "refreshing" : "ready", state.loading ? "badge-neutral" : "badge-status-ready"),
  ].join("");

  elements.connectionPanel.innerHTML = [
    renderMetricCard(
      "Mode",
      badge(state.sourceMode === "live" ? "Live API" : "Fixtures", state.sourceMode === "live" ? "badge-mode-live" : "badge-mode-fixture"),
      escapeHtml(state.sourceMode === "live" ? normalizeBase(state.liveApiBase) : `${scenario.label} fixture scenario`),
      "is-command-card"
    ),
    renderMetricCard(
      "Catalog",
      escapeHtml(`${summary.total_sessions ?? 0} sessions`),
      escapeHtml(`${summary.total_projects ?? 0} projects visible in this dataset`),
      "is-command-card"
    ),
    renderMetricCard(
      "Selection",
      escapeHtml(focusSession?.title || summarizeSessionKey(state.selectedSessionKey) || "No session"),
      escapeHtml(focusProject?.display_name || state.selectedProjectId || "No project"),
      "is-command-card"
    ),
    renderMetricCard(
      "Attention",
      escapeHtml(formatAttentionSummary(summary.status_counts || {})),
      escapeHtml(model?.dataMode === "live" ? "Backed by /api/ui-bundle or live fallback routes." : "Synthetic desktop fixture set for frontend iteration."),
      "is-command-card"
    ),
  ].join("");
}

function renderLibraryMeta(visibleSessions, model) {
  const summary = model.bundle.session_catalog?.summary || {};
  const parts = [
    `${visibleSessions.length} visible`,
    `${summary.total_sessions ?? model.sessions.length} total`,
    `${summary.total_projects ?? model.projects.length} projects`,
  ];
  elements.libraryMeta.textContent = parts.join(" • ");
}

function renderLibrarySummary(model) {
  const summary = model.bundle.session_catalog?.summary || {};
  elements.librarySummary.innerHTML = [
    renderMetricCard("Tool Mix", escapeHtml(formatToolCounts(summary.tool_counts || {})), "Across the current session catalog."),
    renderMetricCard("Attention", escapeHtml(formatAttentionSummary(summary.status_counts || {})), "Sessions that likely need operator review."),
  ].join("");
}

function renderSessionList(sessions) {
  if (!sessions.length) {
    elements.sessionList.innerHTML = renderEmptyCard("No sessions match the current filters.");
    return;
  }
  elements.sessionList.innerHTML = sessions
    .map((session) => {
      const classes = ["session-card"];
      if (session.session_key === state.selectedSessionKey) {
        classes.push("is-active");
      }
      return `
        <button class="${classes.join(" ")}" type="button" data-session-key="${escapeHtml(session.session_key)}">
          <div class="card-topline">
            <div>
              <div class="card-title">${escapeHtml(session.title || session.goal_candidate || session.session_key)}</div>
              <div class="card-subtitle">${escapeHtml(session.project_label || session.project_id || "No project")} • ${escapeHtml(session.updated_at || "Unknown time")}</div>
            </div>
            <div class="badge-row">
              ${badge(session.tool, toolBadgeClass(session.tool))}
              ${badge(`score ${session.score ?? "—"}`, "badge-neutral")}
            </div>
          </div>
          <div class="card-copy">${escapeHtml(session.goal_candidate || "No goal candidate available.")}</div>
          <div class="card-section badge-row">
            ${(session.status_flags || []).map((flag) => badge(flag, statusBadgeClass(flag))).join("")}
            ${badge(session.latest_state || "missing", latestBadgeClass(session.latest_state))}
          </div>
        </button>
      `;
    })
    .join("");

  elements.sessionList.querySelectorAll("[data-session-key]").forEach((node) => {
    node.addEventListener("click", () => {
      const sessionKey = node.getAttribute("data-session-key");
      if (!sessionKey) {
        return;
      }
      selectSession(sessionKey);
    });
  });
}

function renderProjectView(project, detail, model) {
  if (!project) {
    elements.projectTitle.textContent = "No project selected";
    elements.projectMeta.textContent = "Select a session or project to inspect repository state, latest pointers, and ranked local contexts.";
    elements.projectBadges.innerHTML = "";
    setBanner(elements.projectBanner, {
      tone: "empty",
      title: "Project view is waiting for a selection",
      copy: "Choose a session or project to inspect sync signals, ranked contexts, and project-level session coverage.",
    });
    elements.projectSummary.innerHTML = renderMetricCard("Project", "No project", "Project detail will appear here.");
    elements.projectSignals.innerHTML = renderEmptyCard("No project signals available.");
    elements.projectContexts.innerHTML = renderEmptyCard("No ranked local contexts available.");
    elements.projectSessionList.innerHTML = renderEmptyCard("No project sessions available.");
    renderProjectCatalog(model.projects);
    return;
  }

  const projectStatuses = collectProjectStatuses(project);
  elements.projectTitle.textContent = project.display_name || project.project_id;
  elements.projectMeta.textContent = [
    project.git_remote || "No remote configured",
    project.branch || "No branch",
    project.head || "No HEAD",
  ].join(" • ");
  elements.projectBadges.innerHTML = [
    ...(project.active_tools || []).map((tool) => badge(tool, toolBadgeClass(tool))),
    ...projectStatuses.map((flag) => badge(flag, statusBadgeClass(flag))),
  ].join("");

  elements.projectSummary.innerHTML = [
    renderMetricCard("Sessions", escapeHtml(String(project.session_count ?? project.sessions?.length ?? 0)), "Sessions currently associated with this project."),
    renderMetricCard("Recommended", escapeHtml(summarizeSessionKey(project.recommended_session_key) || "None"), "Suggested session to resume first."),
    renderMetricCard("Latest", escapeHtml(formatLatestSnapshotSummary(project.latest_snapshot_ids || {})), "Latest selected snapshots per tool."),
    renderMetricCard("Conflicts", escapeHtml(formatConflictSummary(project.latest_conflicts || {})), "Latest pointer conflicts that may need resolution."),
  ].join("");

  setBanner(elements.projectBanner, buildProjectBanner(project, detail));
  renderProjectSignals(project);
  renderProjectContexts(project, detail);
  renderProjectSessionList(project);
  renderProjectCatalog(model.projects);
}

function renderProjectSignals(project) {
  const latestEntries = Object.entries(project.latest_snapshot_ids || {});
  const conflictEntries = Object.entries(project.latest_conflicts || {}).filter(([, values]) => Array.isArray(values) && values.length);
  const remoteBody = `
    <div class="metric-value is-compact">${escapeHtml(project.git_remote || "No remote configured")}</div>
    <div class="token-list">
      ${token(project.branch || "No branch", true)}
      ${token(project.head || "No HEAD")}
    </div>
  `;
  const latestBody = latestEntries.length
    ? `<div class="token-list">${latestEntries.map(([tool, snapshotId]) => token(`${tool}: ${snapshotId}`)).join("")}</div>`
    : `<div class="metric-value is-compact">No latest snapshots</div>`;
  const conflictBody = conflictEntries.length
    ? conflictEntries
        .map(
          ([tool, values]) => `
            <div class="card-section">
              <div class="panel-kicker">${escapeHtml(tool)}</div>
              <div class="token-list">${values.map((value) => token(value)).join("")}</div>
            </div>
          `
        )
        .join("")
    : `<div class="metric-value is-compact">No latest conflicts</div>`;
  const sessionsBody = `
    <div class="metric-value is-compact">${escapeHtml(String(project.session_count ?? project.sessions?.length ?? 0))} session(s)</div>
    <div class="token-list">
      ${(project.active_tools || []).map((tool) => token(tool, true)).join("")}
      ${project.recommended_session_key ? token(`resume ${summarizeSessionKey(project.recommended_session_key)}`) : ""}
    </div>
  `;

  elements.projectSignals.innerHTML = [
    renderRichPanelCard("Repository", remoteBody, "Remote and current git identity for this project view."),
    renderRichPanelCard("Latest Pointers", latestBody, "Useful for handoff and cross-device resume decisions."),
    renderRichPanelCard("Latest Conflicts", conflictBody, "Conflicts are shown before operator selection is resolved."),
    renderRichPanelCard("Session Coverage", sessionsBody, "How much session activity is currently attached to this project."),
  ].join("");
}

function renderProjectContexts(project, detail) {
  const contexts = resolveProjectContexts(project, detail);
  if (!contexts.length) {
    elements.projectContexts.innerHTML = renderEmptyCard("No ranked local contexts available for the selected project.");
    return;
  }

  const selectedNativeId = detail?.session?.native_session_id || null;
  elements.projectContexts.innerHTML = contexts
    .map((context) => {
      const selected = selectedNativeId && context.session_id === selectedNativeId;
      const reasons = (context.score_reasons || []).slice(0, 4);
      return `
        <article class="context-card">
          <div class="context-card-topline">
            <div>
              <div class="card-title">${escapeHtml(context.title || context.goal_candidate || context.session_id || "Untitled context")}</div>
              <div class="card-subtitle">${escapeHtml(context.tool || "unknown tool")} • ${escapeHtml(context.updated_at || "Unknown time")}</div>
            </div>
            <div class="badge-row">
              ${badge(selected ? "selected" : "candidate", selected ? "badge-context-selected" : "badge-neutral")}
              ${badge(`score ${context.score ?? "—"}`, "badge-neutral")}
            </div>
          </div>
          <div class="card-copy">${escapeHtml(context.goal_candidate || "No goal candidate available.")}</div>
          <div class="card-section token-list">
            ${token(`${context.excerpt_count ?? 0}/${context.total_excerpt_count ?? 0} excerpts`)}
            ${token(`${context.total_user_count ?? 0} user`)}
            ${token(`${context.total_assistant_count ?? 0} assistant`)}
          </div>
          ${reasons.length ? `<div class="card-section token-list">${reasons.map((reason) => token(reason)).join("")}</div>` : ""}
        </article>
      `;
    })
    .join("");
}

function renderProjectSessionList(project) {
  const sessions = project.sessions || [];
  if (!sessions.length) {
    elements.projectSessionList.innerHTML = renderEmptyCard("No sessions are linked to this project.");
    return;
  }

  elements.projectSessionList.innerHTML = sessions
    .map((session) => {
      const classes = ["project-session-card"];
      if (session.session_key === state.selectedSessionKey) {
        classes.push("is-active");
      }
      if (session.session_key === project.recommended_session_key) {
        classes.push("is-recommended");
      }
      return `
        <button class="${classes.join(" ")}" type="button" data-project-session-key="${escapeHtml(session.session_key)}">
          <div class="card-topline">
            <div>
              <div class="card-title">${escapeHtml(session.title || summarizeSessionKey(session.session_key) || session.session_key)}</div>
              <div class="card-subtitle">${escapeHtml(session.updated_at || "Unknown time")}</div>
            </div>
            <div class="badge-row">
              ${badge(session.tool, toolBadgeClass(session.tool))}
              ${session.session_key === project.recommended_session_key ? badge("recommended", "badge-context-selected") : ""}
            </div>
          </div>
          <div class="card-copy">${escapeHtml(session.goal_candidate || "No goal candidate available.")}</div>
          <div class="card-section badge-row">
            ${badge(`score ${session.score ?? "—"}`, "badge-neutral")}
            ${(session.status_flags || []).map((flag) => badge(flag, statusBadgeClass(flag))).join("")}
          </div>
        </button>
      `;
    })
    .join("");

  elements.projectSessionList.querySelectorAll("[data-project-session-key]").forEach((node) => {
    node.addEventListener("click", () => {
      const sessionKey = node.getAttribute("data-project-session-key");
      if (!sessionKey) {
        return;
      }
      selectSession(sessionKey);
    });
  });
}

function renderProjectCatalog(projects) {
  if (!projects.length) {
    elements.projectList.innerHTML = renderEmptyCard("No projects visible.");
    return;
  }

  elements.projectList.innerHTML = projects
    .map((project) => {
      const classes = ["project-card"];
      if (project.project_id === state.selectedProjectId) {
        classes.push("is-active");
      }
      return `
        <button class="${classes.join(" ")}" type="button" data-project-id="${escapeHtml(project.project_id)}">
          <div class="card-topline">
            <div>
              <div class="card-title">${escapeHtml(project.display_name || project.project_id)}</div>
              <div class="card-subtitle">${escapeHtml(project.branch || "No branch")} • ${escapeHtml(project.head || "No HEAD")}</div>
            </div>
            <div class="badge-row">
              ${(project.active_tools || []).map((tool) => badge(tool, toolBadgeClass(tool))).join("")}
            </div>
          </div>
          <div class="card-copy">${escapeHtml(project.git_remote || "No remote configured")}</div>
          <div class="card-section badge-row">
            ${badge(`${project.session_count ?? 0} sessions`, "badge-neutral")}
            ${badge(formatConflictSummary(project.latest_conflicts || {}), hasConflicts(project.latest_conflicts || {}) ? "badge-status-conflict" : "badge-neutral")}
          </div>
        </button>
      `;
    })
    .join("");

  elements.projectList.querySelectorAll("[data-project-id]").forEach((node) => {
    node.addEventListener("click", () => {
      const projectId = node.getAttribute("data-project-id");
      if (!projectId) {
        return;
      }
      selectProject(projectId);
    });
  });
}

function renderDetail(detail) {
  renderDetailTabs();
  if (!detail?.session) {
    elements.detailTitle.textContent = "No session selected";
    elements.detailMeta.textContent = "Open one session to inspect snapshot detail, patch replay guidance, excerpt windows, and handoff markdown.";
    elements.detailBadges.innerHTML = "";
    setBanner(elements.detailBanner, {
      tone: "empty",
      title: "Session detail is waiting for a selection",
      copy: "Select a session from the library or project column to inspect manifest, patch, compare, and handoff panels.",
    });
    elements.detailSummary.innerHTML = renderMetricCard("Session", "No session", "Choose one session from the library or project view.");
    elements.manifestPanel.innerHTML = renderEmptyCard("No manifest is linked to this session yet.");
    elements.patchReplayPanel.innerHTML = renderEmptyCard("No patch replay guidance available.");
    elements.selectedExcerpts.innerHTML = renderEmptyCard("No inspect compare data available.");
    elements.allExcerpts.innerHTML = renderEmptyCard("No inspect compare data available.");
    elements.handoffPanel.textContent = "No handoff markdown linked to this session.";
    return;
  }

  const session = detail.session;
  elements.detailTitle.textContent = session.title || session.goal_candidate || session.session_key;
  elements.detailMeta.textContent = [
    session.project_label || session.project_id || "No project",
    session.updated_at || "Unknown time",
    summarizeSessionKey(session.session_key) || session.session_key,
  ].join(" • ");
  elements.detailBadges.innerHTML = [
    badge(session.tool, toolBadgeClass(session.tool)),
    ...(session.status_flags || []).map((flag) => badge(flag, statusBadgeClass(flag))),
    badge(state.bundle?.dataMode || "fixture", state.bundle?.dataMode === "live" ? "badge-mode-live" : "badge-mode-fixture"),
  ].join("");
  elements.detailSummary.innerHTML = [
    renderMetricCard("Goal", escapeHtml(session.goal_candidate || "No goal candidate"), "Current extracted user goal."),
    renderMetricCard("Latest", escapeHtml(session.latest_state || "missing"), escapeHtml(session.latest_snapshot_id || "No snapshot linked")),
    renderMetricCard("Counts", escapeHtml(`${session.total_user_count || 0} user / ${session.total_assistant_count || 0} assistant`), escapeHtml(`${session.selected_excerpt_count || session.excerpt_count || 0} selected excerpts`)),
    renderMetricCard("Score", escapeHtml(String(session.score ?? "—")), escapeHtml((session.score_reasons || []).slice(0, 2).join(" • ") || "No score reasons available.")),
  ].join("");

  setBanner(elements.detailBanner, buildDetailBanner(detail));
  renderManifest(detail.manifest, session);
  renderPatchReplay(detail.patch_replay);
  renderCompare(detail);
  elements.handoffPanel.textContent = detail.handoff?.markdown || "No handoff markdown linked to this session.";
}

function renderManifest(manifest, session) {
  if (!manifest) {
    elements.manifestPanel.innerHTML = renderEmptyCard("No manifest is linked to this session yet.");
    return;
  }
  const project = manifest.project || {};
  const source = manifest.source || {};
  const warnings = manifest.redaction?.warnings || [];
  elements.manifestPanel.innerHTML = [
    renderPanelCard("Snapshot", manifest.snapshot_id || "Unknown", manifest.created_at || "No created_at"),
    renderPanelCard("Project", project.id || session.project_id || "Unknown", `${project.branch || "No branch"} • ${project.head || "No HEAD"}`),
    renderPanelCard("Provider", source.tool || session.tool, `${source.provider_profile || "unknown"} • ${source.device_id || "unknown device"}`),
    renderPanelCard("Warnings", warnings.length ? warnings.join("\n") : "No redaction warnings", project.dirty ? "Dirty worktree was present during export." : "Public-safe export state."),
  ].join("");
}

function renderPatchReplay(patchReplay) {
  if (!patchReplay) {
    elements.patchReplayPanel.innerHTML = renderEmptyCard("No patch replay guidance available.");
    return;
  }
  elements.patchReplayPanel.innerHTML = [
    renderPanelCard("State", patchReplay.state || "unknown", patchReplay.recommended_mode || "No recommended mode"),
    renderPanelCard("Plain Apply", patchReplay.plain_apply_state || "unknown", patchReplay.patch_path || "No patch artifact"),
    renderPanelCard("3-Way", patchReplay.three_way_state || "unknown", patchReplay.recommended_command || "No command"),
    renderPanelCard("Reason", patchReplay.recommended_reason || "No recommendation reason", "Doctor/status guidance"),
  ].join("");
}

function renderCompare(detail) {
  const context = resolveCompareContext(detail);
  if (!context) {
    elements.selectedExcerpts.innerHTML = renderEmptyCard("No inspect compare data available.");
    elements.allExcerpts.innerHTML = renderEmptyCard("No inspect compare data available.");
    return;
  }
  elements.selectedExcerpts.innerHTML = (context.excerpts || []).map((excerpt) => renderExcerptCard(excerpt, true)).join("");
  elements.allExcerpts.innerHTML = (context.all_excerpts || []).map((excerpt) => renderExcerptCard(excerpt, false)).join("");
}

function renderExcerptCard(excerpt, selectedList) {
  const classes = ["excerpt-card"];
  if (selectedList || excerpt.selected) {
    classes.push("is-selected");
  } else {
    classes.push("is-trimmed");
  }
  const compareTag = selectedList
    ? `selected #${excerpt.selected_index}`
    : excerpt.selected
      ? `selected #${excerpt.selected_index}`
      : "trimmed";
  return `
    <article class="${classes.join(" ")}">
      <div class="card-topline">
        <div class="card-title">${escapeHtml(excerpt.role)}</div>
        <div class="excerpt-meta">${escapeHtml(excerpt.created_at || "unknown")} • ${escapeHtml(compareTag)}</div>
      </div>
      <div class="excerpt-text">${escapeHtml(excerpt.text || "")}</div>
    </article>
  `;
}

function filterSessions(sessions) {
  return sessions.filter((session) => {
    if (state.tool !== "all" && session.tool !== state.tool) {
      return false;
    }
    if (state.status && !(session.status_flags || []).includes(state.status)) {
      return false;
    }
    if (state.q) {
      const haystack = [session.title, session.goal_candidate, session.project_label, session.session_key].join(" ").toLowerCase();
      if (!haystack.includes(state.q.toLowerCase())) {
        return false;
      }
    }
    return true;
  });
}

function coerceSelection(model, visibleSessions) {
  let session = state.selectedSessionKey ? model.sessionMap.get(state.selectedSessionKey) || null : null;
  if (session && !visibleSessions.some((item) => item.session_key === session.session_key)) {
    session = null;
  }

  if (!session && visibleSessions.length) {
    const project = state.selectedProjectId ? model.projectMap.get(state.selectedProjectId) || null : null;
    const preferredKey = pickProjectSessionKey(project, visibleSessions);
    session = (preferredKey && model.sessionMap.get(preferredKey)) || visibleSessions[0];
  }

  let project = null;
  if (session?.project_id) {
    project = model.projectMap.get(session.project_id) || null;
  }
  if (!project && state.selectedProjectId) {
    project = model.projectMap.get(state.selectedProjectId) || null;
  }
  if (!project && model.selectedProjectId) {
    project = model.projectMap.get(model.selectedProjectId) || null;
  }
  if (!project && model.projects.length) {
    project = model.projects[0];
  }

  if (!session && project) {
    const preferredKey = pickProjectSessionKey(project, visibleSessions);
    session = (preferredKey && model.sessionMap.get(preferredKey)) || null;
  }

  const detail = session ? resolveDetailForSession(model, session.session_key) : null;

  if (session && state.selectedSessionKey !== session.session_key) {
    state.selectedSessionKey = session.session_key;
  }
  const resolvedProjectId = session?.project_id || project?.project_id || null;
  if (resolvedProjectId && state.selectedProjectId !== resolvedProjectId) {
    state.selectedProjectId = resolvedProjectId;
    project = model.projectMap.get(resolvedProjectId) || project;
  }

  return { session, project, detail };
}

function resolveDetailForSession(model, sessionKey) {
  if (!sessionKey) {
    return null;
  }
  if (model.detailsByKey[sessionKey]) {
    return model.detailsByKey[sessionKey];
  }
  const session = model.sessionMap.get(sessionKey);
  return session ? { session } : null;
}

function resolveCompareContext(detail) {
  if (!detail?.inspect) {
    return null;
  }
  const session = detail.session || {};
  const tool = session.tool;
  const candidates = tool && Array.isArray(detail.inspect[tool]) ? detail.inspect[tool] : Object.values(detail.inspect).flat();
  if (!Array.isArray(candidates) || !candidates.length) {
    return null;
  }
  return (
    candidates.find((item) => item.session_id === session.native_session_id) ||
    candidates.find((item) => item.session_id === session.session_key) ||
    candidates[0]
  );
}

function resolveProjectContexts(project, detail) {
  if (!project || !detail?.session || detail.session.project_id !== project.project_id) {
    return [];
  }
  const manifestContexts = detail.manifest?.source?.contexts;
  if (Array.isArray(manifestContexts) && manifestContexts.length) {
    return [...manifestContexts].sort((a, b) => (b.score || 0) - (a.score || 0));
  }
  const compareCandidates = detail.inspect?.[detail.session.tool];
  if (Array.isArray(compareCandidates) && compareCandidates.length) {
    return [...compareCandidates].sort((a, b) => (b.score || 0) - (a.score || 0));
  }
  return [];
}

function selectSession(sessionKey) {
  const model = state.bundle;
  if (!model) {
    return;
  }
  const session = model.sessionMap.get(sessionKey) || model.detailsByKey[sessionKey]?.session || null;
  state.selectedSessionKey = sessionKey;
  if (session?.project_id) {
    state.selectedProjectId = session.project_id;
  }
  syncUrl();
  render();
  if (state.sourceMode === "live") {
    loadData();
  }
}

function selectProject(projectId) {
  const model = state.bundle;
  if (!model) {
    return;
  }
  const project = model.projectMap.get(projectId) || null;
  state.selectedProjectId = projectId;
  const currentSession = state.selectedSessionKey ? model.sessionMap.get(state.selectedSessionKey) || null : null;
  if (!currentSession || currentSession.project_id !== projectId) {
    const nextSessionKey = pickProjectSessionKey(project, filterSessions(model.sessions));
    if (nextSessionKey) {
      state.selectedSessionKey = nextSessionKey;
    }
  }
  syncUrl();
  render();
  if (state.sourceMode === "live") {
    loadData();
  }
}

function pickProjectSessionKey(project, candidateSessions = []) {
  if (!project) {
    return candidateSessions[0]?.session_key || null;
  }
  const allowed = candidateSessions.length ? new Set(candidateSessions.map((session) => session.session_key)) : null;
  const candidates = [];
  if (project.recommended_session_key) {
    candidates.push(project.recommended_session_key);
  }
  for (const session of project.sessions || []) {
    candidates.push(session.session_key);
  }
  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (!allowed || allowed.has(candidate)) {
      return candidate;
    }
  }
  return candidateSessions.find((session) => session.project_id === project.project_id)?.session_key || candidateSessions[0]?.session_key || null;
}

function collectProjectStatuses(project) {
  const seen = new Set();
  for (const session of project.sessions || []) {
    for (const flag of session.status_flags || []) {
      seen.add(flag);
    }
  }
  return [...seen];
}

function syncControls() {
  setSegment(elements.sourceFixtures, state.sourceMode === "fixtures");
  setSegment(elements.sourceLive, state.sourceMode === "live");
  setSegment(elements.fixtureClean, state.fixtureScenario === "clean");
  setSegment(elements.fixtureDirty, state.fixtureScenario === "dirty");
  setSegment(elements.fixtureConflict, state.fixtureScenario === "conflict");
  setSegment(elements.historyFilterAll, state.historyFilter === "all");
  setSegment(elements.historyFilterWarn, state.historyFilter === "warn");
  setSegment(elements.historyFilterSync, state.historyFilter === "sync");
  setSegment(elements.historyFilterDetail, state.historyFilter === "detail");
  setSegment(elements.historyGroupSource, state.historyGroupBy === "source");
  setSegment(elements.historyGroupCategory, state.historyGroupBy === "category");
  setSegment(elements.historyGroupFlat, state.historyGroupBy === "flat");
  setSegment(elements.historySortDesc, state.historySortOrder === "desc");
  setSegment(elements.historySortAsc, state.historySortOrder === "asc");
  renderDetailTabs();
  elements.liveApiBase.value = state.liveApiBase;
  elements.toolFilter.value = state.tool;
  elements.statusFilter.value = state.status;
  elements.searchInput.value = state.q;
  const disabled = state.sourceMode === "live";
  elements.fixtureClean.disabled = disabled;
  elements.fixtureDirty.disabled = disabled;
  elements.fixtureConflict.disabled = disabled;
}

function hydrateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  if (mode === "live" || mode === "fixtures") {
    state.sourceMode = mode;
  }
  const scenario = params.get("fixture");
  if (scenario && FIXTURE_SCENARIOS[scenario]) {
    state.fixtureScenario = scenario;
  }
  state.liveApiBase = params.get("api") || state.liveApiBase;
  state.tool = params.get("tool") || state.tool;
  state.status = params.get("status") || state.status;
  state.q = params.get("q") || state.q;
  const detailTab = params.get("detail_tab");
  if (detailTab && DETAIL_TABS[detailTab]) {
    state.detailTab = detailTab;
  }
  state.selectedSessionKey = params.get("session") || state.selectedSessionKey;
  state.selectedProjectId = params.get("project") || state.selectedProjectId;
}

function syncUrl() {
  const params = new URLSearchParams();
  params.set("mode", state.sourceMode);
  params.set("fixture", state.fixtureScenario);
  params.set("api", state.liveApiBase);
  params.set("tool", state.tool);
  if (state.status) {
    params.set("status", state.status);
  }
  if (state.q) {
    params.set("q", state.q);
  }
  if (state.detailTab) {
    params.set("detail_tab", state.detailTab);
  }
  if (state.selectedSessionKey) {
    params.set("session", state.selectedSessionKey);
  }
  if (state.selectedProjectId) {
    params.set("project", state.selectedProjectId);
  }
  const next = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, "", next);
}

function setSegment(node, active) {
  node.classList.toggle("is-active", active);
  node.setAttribute("aria-selected", active ? "true" : "false");
}

function setDetailTab(tabKey) {
  if (!DETAIL_TABS[tabKey]) {
    return;
  }
  state.detailTab = tabKey;
  syncUrl();
  renderDetailTabs();
}

function renderDetailTabs() {
  const tabKey = DETAIL_TABS[state.detailTab] ? state.detailTab : "manifest";
  const config = DETAIL_TABS[tabKey];
  elements.detailTabTitle.textContent = config.title;
  elements.detailTabDescription.textContent = config.description;
  setSegment(elements.detailTabManifest, tabKey === "manifest");
  setSegment(elements.detailTabPatch, tabKey === "patch");
  setSegment(elements.detailTabCompare, tabKey === "compare");
  setSegment(elements.detailTabHandoff, tabKey === "handoff");
  elements.detailPanelManifest.hidden = tabKey !== "manifest";
  elements.detailPanelPatch.hidden = tabKey !== "patch";
  elements.detailPanelCompare.hidden = tabKey !== "compare";
  elements.detailPanelHandoff.hidden = tabKey !== "handoff";
}

function renderMetricCard(label, value, note, extraClass = "") {
  return `
    <article class="metric-card ${extraClass}">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${value}</div>
      <div class="metric-note">${note}</div>
    </article>
  `;
}

function renderPanelCard(label, value, note) {
  return `
    <article class="panel-card">
      <div class="panel-kicker">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(String(value || "—"))}</div>
      <div class="panel-note">${escapeHtml(String(note || ""))}</div>
    </article>
  `;
}

function renderRichPanelCard(label, bodyHtml, note) {
  return `
    <article class="panel-card">
      <div class="panel-kicker">${escapeHtml(label)}</div>
      ${bodyHtml}
      <div class="panel-note">${escapeHtml(String(note || ""))}</div>
    </article>
  `;
}

function renderEmptyCard(message) {
  return `<div class="empty-card">${message}</div>`;
}

function badge(label, className) {
  return `<span class="badge ${className}">${escapeHtml(String(label))}</span>`;
}

function token(label, strong = false) {
  return `<span class="token${strong ? " is-strong" : ""}">${escapeHtml(String(label))}</span>`;
}

function toolBadgeClass(tool) {
  return tool === "codex" ? "badge-tool-codex" : "badge-tool-claude";
}

function statusBadgeClass(flag) {
  return `badge-status-${flag}`;
}

function latestBadgeClass(stateValue) {
  if (stateValue === "conflict") {
    return "badge-status-conflict";
  }
  if (stateValue === "ready") {
    return "badge-mode-live";
  }
  return "badge-neutral";
}

function summarizeSessionKey(sessionKey) {
  if (!sessionKey) {
    return "";
  }
  const parts = String(sessionKey).split(":");
  return parts[parts.length - 1] || sessionKey;
}

function formatToolCounts(toolCounts) {
  const entries = Object.entries(toolCounts || {});
  if (!entries.length) {
    return "No tool data";
  }
  return entries.map(([tool, count]) => `${tool} ${count}`).join(" • ");
}

function formatAttentionSummary(statusCounts) {
  const entries = Object.entries(statusCounts || {}).filter(([, count]) => Number(count) > 0);
  if (!entries.length) {
    return "No flagged sessions";
  }
  return entries.map(([flag, count]) => `${flag} ${count}`).join(" • ");
}

function formatLatestSnapshotSummary(latestSnapshotIds) {
  const entries = Object.entries(latestSnapshotIds || {}).filter(([, value]) => Boolean(value));
  if (!entries.length) {
    return "No latest snapshots";
  }
  return entries.map(([tool, value]) => `${tool}: ${summarizeSessionKey(value)}`).join(" • ");
}

function formatConflictSummary(latestConflicts) {
  const entries = Object.entries(latestConflicts || {}).filter(([, values]) => Array.isArray(values) && values.length);
  if (!entries.length) {
    return "No conflicts";
  }
  return entries.map(([tool, values]) => `${tool} ${values.length}`).join(" • ");
}

function hasConflicts(latestConflicts) {
  return Object.values(latestConflicts || {}).some((values) => Array.isArray(values) && values.length);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${url}`);
  }
  return response.json();
}

async function runRescan(source = "command") {
  if (state.loading) {
    return;
  }
  if (state.sourceMode !== "live") {
    setActionFeedback("warn", "Rescan is only available in Live API mode.");
    logActivity("warn", "Rescan local session catalogs", "Rescan was blocked because the workbench is not in Live API mode.", source, "Sync");
    return;
  }
  const base = normalizeBase(state.liveApiBase);
  try {
    setActionFeedback("info", "Rescanning local catalogs…");
    const payload = await fetchJsonWithInit(`${base}/api/sessions/rescan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tools: state.tool === "all" ? ["codex", "claude"] : [state.tool] }),
    });
    setActionFeedback("success", `Rescan complete: ${payload.session_count || 0} session(s) across ${payload.rescanned_tools?.join(", ") || "tools"}.`);
    logActivity("success", "Rescan local session catalogs", `Rescanned ${payload.session_count || 0} session(s) across ${payload.rescanned_tools?.join(", ") || "tools"}.`, source, "Sync");
    await loadData();
  } catch (error) {
    setActionFeedback("warn", `Rescan failed: ${error?.message || String(error)}`);
    logActivity("warn", "Rescan local session catalogs", error?.message || String(error), source, "Sync");
  }
}

function openLiveApi(source = "command") {
  const base = normalizeBase(state.liveApiBase);
  const params = new URLSearchParams();
  params.set("tool", state.tool);
  if (state.status) {
    params.set("status", state.status);
  }
  if (state.q) {
    params.set("q", state.q);
  }
  if (state.selectedSessionKey) {
    params.set("selected_session_key", state.selectedSessionKey);
  }
  if (state.selectedProjectId) {
    params.set("selected_project_id", state.selectedProjectId);
  }
  params.set("active_view", "session-detail");
  params.set("data_mode", "live");
  window.open(`${base}/api/ui-bundle?${params.toString()}`, "_blank", "noopener,noreferrer");
  setActionFeedback("info", "Opened the live API bundle in a new tab.");
  logActivity("info", "Open live API bundle", "Opened the current UI bundle JSON in a new tab.", source, "Sync");
}

async function copySessionKey(source = "command") {
  if (!state.selectedSessionKey) {
    setActionFeedback("warn", "No session is selected yet.");
    logActivity("warn", "Copy selected session key", "Copy was blocked because no session is selected.", source, "Session");
    return;
  }
  try {
    if (!navigator?.clipboard?.writeText) {
      throw new Error("Clipboard API unavailable");
    }
    await navigator.clipboard.writeText(state.selectedSessionKey);
    setActionFeedback("success", `Copied session key: ${state.selectedSessionKey}`);
    logActivity("success", "Copy selected session key", `Copied ${state.selectedSessionKey} to the clipboard.`, source, "Session");
  } catch (error) {
    setActionFeedback("warn", `Could not copy session key: ${error?.message || String(error)}`);
    logActivity("warn", "Copy selected session key", error?.message || String(error), source, "Session");
  }
}

function renderActionFeedback() {
  const feedback = state.actionFeedback;
  if (!feedback) {
    elements.actionFeedback.textContent = "";
    return;
  }
  elements.actionFeedback.innerHTML = badge(feedback.message, feedback.className);
}

function setActionFeedback(kind, message) {
  const className =
    kind === "success" ? "badge-feedback-success" :
    kind === "warn" ? "badge-feedback-warn" :
    "badge-feedback-info";
  state.actionFeedback = { kind, message, className };
  renderActionFeedback();
}

function clearSurfaceStates() {
  [elements.librarySurface, elements.projectSurface, elements.detailSurface].forEach((element) => {
    element.classList.remove("surface-state-empty", "surface-state-error", "surface-state-dirty", "surface-state-conflict");
  });
}

function setSurfaceState(element, tone) {
  if (!element) {
    return;
  }
  element.classList.remove("surface-state-empty", "surface-state-error", "surface-state-dirty", "surface-state-conflict");
  if (tone) {
    element.classList.add(`surface-state-${tone}`);
  }
}

function setBanner(element, config) {
  if (!element) {
    return;
  }
  element.classList.remove("banner-state-empty", "banner-state-error", "banner-state-dirty", "banner-state-conflict");
  if (!config) {
    element.hidden = true;
    element.innerHTML = "";
    return;
  }
  element.hidden = false;
  if (config.tone) {
    element.classList.add(`banner-state-${config.tone}`);
  }
  const actions = Array.isArray(config.actions) && config.actions.length
    ? `
        <div class="banner-actions">
          ${config.actions
            .map(
              (action) => `
                <button
                  class="command-button banner-action ${bannerActionClass(config.tone)}"
                  type="button"
                  data-banner-command="${escapeHtml(action.command)}"
                  title="${escapeHtml(action.label)}"
                >
                  ${escapeHtml(action.label)}
                </button>
              `
            )
            .join("")}
        </div>
      `
    : "";
  element.innerHTML = `
    <div class="banner-title">${escapeHtml(config.title || "")}</div>
    <div class="banner-copy">${escapeHtml(config.copy || "")}</div>
    ${actions}
  `;
}

function renderStateLayers(project, detail, visibleSessions, model) {
  clearSurfaceStates();
  const workspaceBanner = buildWorkspaceBanner(project, detail, visibleSessions, model);
  setBanner(elements.workspaceBanner, workspaceBanner);
  if (workspaceBanner?.tone) {
    setSurfaceState(elements.librarySurface, workspaceBanner.tone);
  }
  const projectBanner = buildProjectBanner(project, detail);
  setBanner(elements.projectBanner, projectBanner);
  if (projectBanner?.tone) {
    setSurfaceState(elements.projectSurface, projectBanner.tone);
  }
  const detailBanner = buildDetailBanner(detail);
  setBanner(elements.detailBanner, detailBanner);
  if (detailBanner?.tone) {
    setSurfaceState(elements.detailSurface, detailBanner.tone);
  }
  if (!visibleSessions.length) {
    setSurfaceState(elements.librarySurface, "empty");
  }
}

function buildWorkspaceBanner(project, detail, visibleSessions, model) {
  if (!visibleSessions.length) {
    return {
      tone: "empty",
      title: "No sessions match the current filters",
      copy: "Broaden the tool, status, or search filters, or switch to another data source to repopulate the workbench.",
      actions: [
        { label: "Clear filters", command: "clear_filters" },
        { label: "Switch to fixtures", command: "switch_to_fixtures" },
      ],
    };
  }
  if (detail?.session?.status_flags?.includes("conflict") || hasConflicts(project?.latest_conflicts || {})) {
    return {
      tone: "conflict",
      title: "Attention: latest selection conflict is present",
      copy: "The current project or selected session has competing latest snapshot candidates that should be resolved before handoff or replay.",
      actions: [
        { label: "Review patch guidance", command: "focus_patch_tab" },
        { label: "Inspect excerpts", command: "focus_compare_tab" },
      ],
    };
  }
  if (detail?.manifest?.project?.dirty || detail?.session?.status_flags?.includes("dirty")) {
    return {
      tone: "dirty",
      title: "Dirty worktree state is part of this handoff",
      copy: "The current selection includes uncommitted work or replay-sensitive patch state, so import strategy matters.",
      actions: [
        { label: "Review patch replay", command: "focus_patch_tab" },
        { label: "Copy session key", command: "copy_session_key" },
      ],
    };
  }
  return null;
}

function buildProjectBanner(project, detail) {
  if (!project) {
    return {
      tone: "empty",
      title: "Project view has no active project",
      copy: "Select a session or project to inspect repository state, latest pointers, and ranked context candidates.",
    };
  }
  if (hasConflicts(project.latest_conflicts || {})) {
    return {
      tone: "conflict",
      title: "Latest pointer conflict needs operator choice",
      copy: "This project has multiple competing latest snapshot candidates. The UI should expose selection before replay/import continues.",
      actions: [
        { label: "Use recommended session", command: "focus_recommended_session" },
        { label: "Open live API payload", command: "open_live_api" },
      ],
    };
  }
  const dirtySession = (project.sessions || []).find((session) => (session.status_flags || []).includes("dirty"));
  if (dirtySession || detail?.manifest?.project?.dirty) {
    return {
      tone: "dirty",
      title: "Dirty or patch-bearing session is active in this project",
      copy: "One or more sessions in this project carry dirty worktree or patch replay state and should be treated carefully during handoff.",
      actions: [
        { label: "Inspect patch session", command: "focus_patch_tab" },
        { label: "Review handoff", command: "focus_handoff_tab" },
      ],
    };
  }
  return null;
}

function buildDetailBanner(detail) {
  if (!detail?.session) {
    return {
      tone: "empty",
      title: "No session detail selected",
      copy: "Choose a session to inspect manifest, patch guidance, excerpts, and handoff content.",
    };
  }
  const session = detail.session;
  if ((session.status_flags || []).includes("conflict") || session.latest_state === "conflict") {
    return {
      tone: "conflict",
      title: "This session is blocked on latest selection conflict",
      copy: "Resume/import decisions should account for multiple latest candidates before replay or handoff is treated as final.",
      actions: [
        { label: "Inspect excerpt history", command: "focus_compare_tab" },
        { label: "Open live API payload", command: "open_live_api" },
      ],
    };
  }
  if ((session.status_flags || []).includes("dirty") || detail.manifest?.project?.dirty || detail.patch_replay?.state === "blocked") {
    return {
      tone: "dirty",
      title: "This session carries unfinished local work",
      copy: "Patch replay and import should be treated as safety-sensitive because the source worktree or patch state is not clean.",
      actions: [
        { label: "Review patch replay", command: "focus_patch_tab" },
        { label: "Copy session key", command: "copy_session_key" },
      ],
    };
  }
  return null;
}

function toneBadgeClass(tone) {
  if (tone === "conflict" || tone === "error") {
    return "badge-error";
  }
  if (tone === "dirty") {
    return "badge-feedback-warn";
  }
  if (tone === "empty") {
    return "badge-neutral";
  }
  return "badge-feedback-info";
}

function bannerActionClass(tone) {
  if (tone === "conflict" || tone === "error") {
    return "is-danger";
  }
  if (tone === "dirty") {
    return "";
  }
  return "";
}

async function fetchJsonWithInit(url, init) {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${url}`);
  }
  return response.json();
}

async function executeCommand(commandId, context = {}) {
  const command = COMMANDS[commandId];
  if (!command) {
    return;
  }
  const availability = getCommandAvailability(commandId);
  if (!availability.enabled && commandId !== "open_palette") {
    setActionFeedback("warn", availability.reason || "This command is not available right now.");
    logActivity("warn", command.label, availability.reason || "Command is unavailable.", context.source || "command");
    return;
  }
  try {
    switch (commandId) {
      case "open_palette":
        openCommandPalette();
        logActivity("info", command.label, "Opened the command palette.", context.source);
        return;
      case "reload_data":
        setActionFeedback("info", "Reloading current source…");
        logActivity("info", command.label, "Refreshing the active data source.", context.source, command.group);
        await loadData();
        return;
      case "rescan_catalog":
        await runRescan(context.source || "command");
        return;
      case "open_live_api":
        openLiveApi(context.source || "command");
        return;
      case "copy_session_key":
        await copySessionKey(context.source || "command");
        return;
      case "switch_to_fixtures":
        state.sourceMode = "fixtures";
        syncControls();
        setActionFeedback("info", "Switched to fixture mode.");
        logActivity("info", command.label, "Using synthetic desktop fixtures.", context.source, command.group);
        await loadData();
        return;
      case "switch_to_live":
        state.sourceMode = "live";
        syncControls();
        setActionFeedback("info", "Switched to live API mode.");
        logActivity("info", command.label, "Using a live local API server.", context.source, command.group);
        await loadData();
        return;
      case "focus_patch_tab":
        setDetailTab("patch");
        setActionFeedback("info", "Focused patch guidance.");
        logActivity("info", command.label, "Detail column switched to the patch replay tab.", context.source, command.group);
        return;
      case "focus_compare_tab":
        setDetailTab("compare");
        setActionFeedback("info", "Focused excerpt compare.");
        logActivity("info", command.label, "Detail column switched to the excerpt compare tab.", context.source, command.group);
        return;
      case "focus_handoff_tab":
        setDetailTab("handoff");
        setActionFeedback("info", "Focused handoff markdown.");
        logActivity("info", command.label, "Detail column switched to the handoff tab.", context.source, command.group);
        return;
      case "focus_recommended_session": {
        const project = state.bundle?.selectedProject || state.bundle?.projectMap?.get?.(state.selectedProjectId) || null;
        const nextSessionKey = pickProjectSessionKey(project, filterSessions(state.bundle?.sessions || []));
        if (!nextSessionKey) {
          setActionFeedback("warn", "No recommended project session is available.");
          logActivity("warn", command.label, "No recommended project session could be selected.", context.source, command.group);
          return;
        }
        selectSession(nextSessionKey);
        setActionFeedback("success", `Opened recommended session: ${nextSessionKey}`);
        logActivity("success", command.label, `Selected recommended session ${nextSessionKey}.`, context.source, command.group);
        return;
      }
      case "clear_filters":
        state.tool = "all";
        state.status = "";
        state.q = "";
        syncControls();
        setActionFeedback("success", "Cleared tool, status, and search filters.");
        logActivity("success", command.label, "Workbench filters reset to the broadest view.", context.source, command.group);
        render();
        if (state.sourceMode === "live") {
          await loadData();
        }
        return;
      case "export_activity_log": {
        logActivity("success", command.label, "Exported the current browser session audit trail.", context.source, command.group);
        exportActivityLog();
        setActionFeedback("success", "Exported command history JSON.");
        return;
      }
      case "clear_activity_log":
        state.activityLog = [];
        state.historySequence = 0;
        persistHistory();
        renderActivityLog();
        setActionFeedback("info", "Cleared recent activity.");
        return;
      default:
        return;
    }
  } finally {
    if (context.source === "palette" || context.closePalette) {
      closeCommandPalette();
    }
  }
}

function openCommandPalette() {
  state.commandPaletteOpen = true;
  state.commandActiveIndex = 0;
  elements.commandPaletteOverlay.hidden = false;
  renderCommandPalette();
  requestAnimationFrame(() => {
    elements.commandSearchInput.focus();
    elements.commandSearchInput.select();
  });
}

function closeCommandPalette() {
  state.commandPaletteOpen = false;
  state.commandQuery = "";
  state.commandActiveIndex = 0;
  elements.commandSearchInput.value = "";
  elements.commandPaletteOverlay.hidden = true;
  renderCommandPalette();
}

function renderCommandPalette() {
  const model = buildCommandPaletteModel();
  if (!model.selectable.length) {
    state.commandActiveIndex = 0;
  } else {
    state.commandActiveIndex = Math.max(0, Math.min(state.commandActiveIndex, model.selectable.length - 1));
  }
  elements.commandPaletteMeta.textContent = model.filtered.length
    ? `${model.filtered.length} command(s) • arrows cycle the current group • PageUp/PageDown jumps groups • shortcuts run directly`
    : "No commands match the current search";
  if (!model.filtered.length) {
    elements.commandPaletteList.innerHTML = renderEmptyCard("No commands match the current search.");
    return;
  }

  elements.commandPaletteList.innerHTML = `
    <div class="palette-command-list">
      ${model.groups
        .map(
          (group) => `
            <section class="palette-command-group">
              <div class="palette-group-title">${escapeHtml(group.name)}${group.selectableItems.length ? ` • ${group.selectableItems.length}` : ""}</div>
              ${group.items
                .map((item) => {
                  const activeCommandId = model.selectable[state.commandActiveIndex]?.id || null;
                  const activeClass = item.availability.enabled && item.id === activeCommandId ? "is-active" : "";
                  return `
                    <button
                      class="palette-command ${activeClass}"
                      type="button"
                      data-command-id="${escapeHtml(item.id)}"
                      ${item.availability.enabled ? "" : "disabled"}
                      title="${escapeHtml(item.availability.enabled ? item.command.description : item.availability.reason || item.command.description)}"
                    >
                      <div class="palette-command-topline">
                        <div class="card-title">${escapeHtml(item.command.label)}</div>
                        <div class="badge-row">
                          ${item.command.shortcut ? `<span class="palette-command-shortcut">${escapeHtml(item.command.shortcut)}</span>` : ""}
                          <div class="palette-command-meta">${escapeHtml(item.id)}</div>
                        </div>
                      </div>
                      <div class="card-copy">${escapeHtml(item.command.description)}</div>
                      ${
                        item.availability.enabled
                          ? ""
                          : `<div class="palette-command-reason">${escapeHtml(item.availability.reason || "Unavailable")}</div>`
                      }
                    </button>
                  `;
                })
                .join("")}
            </section>
          `
        )
        .join("")}
    </div>
  `;
}

function matchesCommandQuery(id, command, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return true;
  }
  const haystack = [id, command.label, command.description, ...(command.keywords || [])].join(" ").toLowerCase();
  return haystack.includes(needle);
}

function buildCommandPaletteModel() {
  const filtered = Object.entries(COMMANDS).filter(([id, command]) => matchesCommandQuery(id, command, state.commandQuery));
  const groups = [];
  const groupMap = new Map();
  const selectable = [];

  for (const [id, command] of filtered) {
    const groupName = command.group || "Other";
    let group = groupMap.get(groupName);
    if (!group) {
      group = { name: groupName, items: [], selectableItems: [] };
      groups.push(group);
      groupMap.set(groupName, group);
    }
    const item = {
      id,
      command,
      availability: getCommandAvailability(id),
      group,
      globalSelectableIndex: null,
      groupSelectableIndex: null,
    };
    if (item.availability.enabled) {
      item.groupSelectableIndex = group.selectableItems.length;
      item.globalSelectableIndex = selectable.length;
      group.selectableItems.push(item);
      selectable.push(item);
    }
    group.items.push(item);
  }

  return { filtered, groups, selectable };
}

function logActivity(kind, title, message, source = "system", group = null) {
  const timestamp = new Date();
  const entry = {
    kind,
    title,
    message,
    source,
    group: group || inferHistoryGroup(title, source),
    timestamp: timestamp.toISOString(),
    at: formatHistoryTime(timestamp.toISOString()),
    sequence: state.historySequence + 1,
  };
  state.historySequence = entry.sequence;
  state.activityLog = [entry, ...state.activityLog].slice(0, HISTORY_ENTRY_LIMIT);
  persistHistory();
  renderActivityLog();
}

function renderActivityLog() {
  const filteredEntries = getVisibleHistoryEntries();
  if (!filteredEntries.length) {
    const emptyMessage = state.activityLog.length
      ? "No command history matches the current audit filter."
      : "No command history for this browser session yet.";
    elements.activityLog.innerHTML = renderEmptyCard(emptyMessage);
    return;
  }
  if (state.historyGroupBy === "flat") {
    elements.activityLog.innerHTML = filteredEntries.map((entry) => renderHistoryEntry(entry)).join("");
    return;
  }

  const grouped = new Map();
  for (const entry of filteredEntries) {
    const groupLabel = state.historyGroupBy === "source" ? formatHistorySource(entry.source) : entry.group || "History";
    if (!grouped.has(groupLabel)) {
      grouped.set(groupLabel, []);
    }
    grouped.get(groupLabel).push(entry);
  }

  elements.activityLog.innerHTML = [...grouped.entries()]
    .map(
      ([groupLabel, entries]) => `
        <section class="activity-log-group">
          <div class="activity-log-group-title">${escapeHtml(groupLabel)} • ${entries.length}</div>
          ${entries.map((entry) => renderHistoryEntry(entry)).join("")}
        </section>
      `
    )
    .join("");
}

function activityBadgeClass(kind) {
  if (kind === "success") {
    return "badge-feedback-success";
  }
  if (kind === "warn") {
    return "badge-feedback-warn";
  }
  return "badge-feedback-info";
}

function getCommandAvailability(commandId) {
  switch (commandId) {
    case "rescan_catalog":
      if (state.sourceMode !== "live") {
        return { enabled: false, reason: "Switch to Live API mode to rescan local catalogs." };
      }
      if (state.loading) {
        return { enabled: false, reason: "Wait for the current refresh to finish." };
      }
      return { enabled: true, reason: "" };
    case "open_live_api":
      return state.liveApiBase ? { enabled: true, reason: "" } : { enabled: false, reason: "Provide a live API base first." };
    case "copy_session_key":
      return state.selectedSessionKey ? { enabled: true, reason: "" } : { enabled: false, reason: "Select a session before copying its key." };
    case "focus_patch_tab":
    case "focus_compare_tab":
    case "focus_handoff_tab":
      return state.selectedSessionKey ? { enabled: true, reason: "" } : { enabled: false, reason: "Select a session to focus detail panels." };
    case "focus_recommended_session": {
      const project = state.bundle?.selectedProject || state.bundle?.projectMap?.get?.(state.selectedProjectId) || null;
      const nextSessionKey = pickProjectSessionKey(project, filterSessions(state.bundle?.sessions || []));
      return nextSessionKey
        ? { enabled: true, reason: "" }
        : { enabled: false, reason: "No recommended session is available for the current project." };
    }
    case "clear_activity_log":
      return state.activityLog.length ? { enabled: true, reason: "" } : { enabled: false, reason: "History is already empty for this browser session." };
    case "export_activity_log":
      return { enabled: true, reason: "" };
    default:
      return { enabled: true, reason: "" };
  }
}

function inferHistoryGroup(title, source) {
  const lower = `${title} ${source}`.toLowerCase();
  if (lower.includes("rescan") || lower.includes("api") || lower.includes("live")) {
    return "Sync";
  }
  if (lower.includes("patch") || lower.includes("excerpt") || lower.includes("handoff")) {
    return "Detail";
  }
  if (lower.includes("session") || lower.includes("copy")) {
    return "Session";
  }
  return "General";
}

function persistHistory() {
  try {
    window.sessionStorage.setItem(
      HISTORY_STORAGE_KEY,
      JSON.stringify({
        session: {
          id: state.historySessionId,
          started_at: state.historySessionStartedAt,
          sequence: state.historySequence,
          retained_entry_limit: HISTORY_ENTRY_LIMIT,
        },
        entries: state.activityLog,
      })
    );
  } catch (error) {
    console.warn("Could not persist command history", error);
  }
}

function hydrateHistory() {
  try {
    const raw = window.sessionStorage.getItem(HISTORY_STORAGE_KEY);
    const fallbackId = createHistorySessionId();
    const fallbackStartedAt = new Date().toISOString();

    if (!raw) {
      state.historySessionId = fallbackId;
      state.historySessionStartedAt = fallbackStartedAt;
      state.historySequence = 0;
      return;
    }

    const payload = JSON.parse(raw);
    if (Array.isArray(payload)) {
      state.historySessionId = fallbackId;
      state.historySessionStartedAt = fallbackStartedAt;
      state.activityLog = normalizeHistoryEntries(payload);
      state.historySequence = Math.max(0, ...state.activityLog.map((entry) => entry.sequence || 0));
      return;
    }
    if (!payload || typeof payload !== "object" || !Array.isArray(payload.entries)) {
      state.historySessionId = fallbackId;
      state.historySessionStartedAt = fallbackStartedAt;
      state.historySequence = 0;
      return;
    }

    state.historySessionId = payload.session?.id || fallbackId;
    state.historySessionStartedAt = payload.session?.started_at || fallbackStartedAt;
    state.activityLog = normalizeHistoryEntries(payload.entries);
    state.historySequence =
      Number.isFinite(payload.session?.sequence) && payload.session.sequence > 0
        ? payload.session.sequence
        : Math.max(0, ...state.activityLog.map((entry) => entry.sequence || 0));
  } catch (error) {
    console.warn("Could not hydrate command history", error);
    state.historySessionId = createHistorySessionId();
    state.historySessionStartedAt = new Date().toISOString();
    state.historySequence = 0;
  }
}

function moveCommandSelection(delta) {
  const model = buildCommandPaletteModel();
  if (!model.selectable.length) {
    return;
  }
  const activeItem = model.selectable[state.commandActiveIndex] || model.selectable[0];
  const groupItems = activeItem?.group?.selectableItems || [];
  if (!groupItems.length) {
    return;
  }
  const currentGroupIndex = activeItem.groupSelectableIndex ?? 0;
  const nextGroupIndex = (currentGroupIndex + delta + groupItems.length) % groupItems.length;
  state.commandActiveIndex = groupItems[nextGroupIndex].globalSelectableIndex;
  renderCommandPalette();
  scrollActiveCommandIntoView();
}

function activateSelectedCommand() {
  const model = buildCommandPaletteModel();
  const activeCommandId = model.selectable[state.commandActiveIndex]?.id;
  if (!activeCommandId) {
    return;
  }
  executeCommand(activeCommandId, { source: "palette" });
}

function setHistoryFilter(filter) {
  state.historyFilter = filter;
  syncControls();
  renderActivityLog();
}

function setHistoryGroupBy(groupBy) {
  state.historyGroupBy = groupBy;
  syncControls();
  renderActivityLog();
}

function setHistorySortOrder(sortOrder) {
  state.historySortOrder = sortOrder;
  syncControls();
  renderActivityLog();
}

function matchesHistoryFilter(entry, filter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "warn") {
    return entry.kind === "warn";
  }
  if (filter === "sync") {
    return entry.group === "Sync";
  }
  if (filter === "detail") {
    return entry.group === "Detail";
  }
  return true;
}

function getVisibleHistoryEntries() {
  const filtered = state.activityLog.filter((entry) => matchesHistoryFilter(entry, state.historyFilter));
  const sorted = [...filtered].sort((left, right) => compareHistoryEntries(left, right, state.historySortOrder));
  return sorted;
}

function compareHistoryEntries(left, right, sortOrder) {
  const leftValue = historySortValue(left);
  const rightValue = historySortValue(right);
  if (leftValue === rightValue) {
    return sortOrder === "asc" ? left.sequence - right.sequence : right.sequence - left.sequence;
  }
  return sortOrder === "asc" ? leftValue - rightValue : rightValue - leftValue;
}

function historySortValue(entry) {
  const parsed = entry.timestamp ? Date.parse(entry.timestamp) : NaN;
  if (!Number.isNaN(parsed)) {
    return parsed;
  }
  return entry.sequence || 0;
}

function renderHistoryEntry(entry) {
  return `
    <article class="activity-log-entry">
      <div class="activity-log-entry-topline">
        <div class="card-title">${escapeHtml(entry.title)}</div>
        <div class="badge-row">
          ${badge(entry.kind, activityBadgeClass(entry.kind))}
          ${renderHistorySecondaryBadges(entry)}
        </div>
      </div>
      <div class="card-copy">${escapeHtml(entry.message)}</div>
      <div class="activity-log-meta">${escapeHtml(formatHistoryMeta(entry))}</div>
    </article>
  `;
}

function renderHistorySecondaryBadges(entry) {
  const badges = [];
  if (state.historyGroupBy !== "source") {
    badges.push(badge(formatHistorySource(entry.source), "badge-neutral"));
  }
  if (state.historyGroupBy !== "category") {
    badges.push(badge(entry.group || "History", "badge-neutral"));
  }
  return badges.join("");
}

function formatHistoryMeta(entry) {
  const parts = [entry.at || "unknown time"];
  if (entry.timestamp) {
    parts.push(entry.timestamp);
  }
  if (entry.sequence) {
    parts.push(`event #${entry.sequence}`);
  }
  return parts.join(" • ");
}

function formatHistorySource(source) {
  switch (source) {
    case "toolbar":
      return "Toolbar";
    case "palette":
      return "Palette";
    case "banner":
      return "Banner";
    case "shortcut":
      return "Shortcut";
    case "command":
      return "Command";
    case "system":
      return "System";
    default:
      return humanizeKebabLike(source || "unknown");
  }
}

function normalizeHistoryEntries(entries) {
  const total = Array.isArray(entries) ? entries.length : 0;
  return (Array.isArray(entries) ? entries : [])
    .filter((entry) => entry && typeof entry === "object")
    .slice(0, HISTORY_ENTRY_LIMIT)
    .map((entry, index) => {
      const timestamp = typeof entry.timestamp === "string" ? entry.timestamp : null;
      const sequence = Number.isFinite(entry.sequence) && entry.sequence > 0 ? entry.sequence : total - index;
      return {
        kind: typeof entry.kind === "string" ? entry.kind : "info",
        title: typeof entry.title === "string" ? entry.title : "Untitled event",
        message: typeof entry.message === "string" ? entry.message : "",
        source: typeof entry.source === "string" ? entry.source : "system",
        group: typeof entry.group === "string" ? entry.group : inferHistoryGroup(entry.title || "", entry.source || "system"),
        timestamp,
        at: typeof entry.at === "string" ? entry.at : formatHistoryTime(timestamp || new Date().toISOString()),
        sequence,
      };
    });
}

function formatHistoryTime(timestamp) {
  const date = timestamp ? new Date(timestamp) : new Date();
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function createHistorySessionId() {
  const random = Math.random().toString(36).slice(2, 8);
  return `desktop-${Date.now().toString(36)}-${random}`;
}

function exportActivityLog() {
  const entries = getVisibleHistoryEntries();
  const payload = {
    schema_version: "aiss-desktop-command-history/v1",
    exported_at: new Date().toISOString(),
    history_session: {
      id: state.historySessionId,
      started_at: state.historySessionStartedAt,
      retained_entry_limit: HISTORY_ENTRY_LIMIT,
      stored_entry_count: state.activityLog.length,
      exported_entry_count: entries.length,
    },
    workbench: {
      source_mode: state.sourceMode,
      fixture_scenario: state.fixtureScenario,
      live_api_base: normalizeBase(state.liveApiBase),
      selected_session_key: state.selectedSessionKey,
      selected_project_id: state.selectedProjectId,
    },
    view: {
      filter: state.historyFilter,
      group_by: state.historyGroupBy,
      sort_order: state.historySortOrder,
    },
    entries,
  };
  const safeTimestamp = payload.exported_at.replaceAll(":", "-");
  downloadJsonFile(`aiss-command-history-${safeTimestamp}.json`, payload);
}

function downloadJsonFile(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function jumpCommandGroup(direction) {
  const model = buildCommandPaletteModel();
  const selectableGroups = model.groups.filter((group) => group.selectableItems.length);
  if (!selectableGroups.length) {
    return;
  }
  const activeItem = model.selectable[state.commandActiveIndex] || model.selectable[0];
  const activeGroupName = activeItem?.group?.name || selectableGroups[0].name;
  const currentGroupIndex = Math.max(
    0,
    selectableGroups.findIndex((group) => group.name === activeGroupName)
  );
  const nextGroup = selectableGroups[(currentGroupIndex + direction + selectableGroups.length) % selectableGroups.length];
  const targetItem =
    direction > 0
      ? nextGroup.selectableItems[0]
      : nextGroup.selectableItems[nextGroup.selectableItems.length - 1];
  if (!targetItem) {
    return;
  }
  state.commandActiveIndex = targetItem.globalSelectableIndex;
  renderCommandPalette();
  scrollActiveCommandIntoView();
}

function scrollActiveCommandIntoView() {
  requestAnimationFrame(() => {
    const model = buildCommandPaletteModel();
    const activeCommandId = model.selectable[state.commandActiveIndex]?.id;
    if (!activeCommandId) {
      return;
    }
    const node = elements.commandPaletteList.querySelector(`[data-command-id="${CSS.escape(activeCommandId)}"]`);
    node?.scrollIntoView({ block: "nearest" });
  });
}

function findCommandShortcutMatch(event) {
  for (const [commandId, command] of Object.entries(COMMANDS)) {
    if (!command.shortcut || commandId === "open_palette") {
      continue;
    }
    if (!shortcutMatchesEvent(command.shortcut, event)) {
      continue;
    }
    const availability = getCommandAvailability(commandId);
    if (availability.enabled) {
      return commandId;
    }
  }
  return null;
}

function shortcutMatchesEvent(shortcut, event) {
  const parts = String(shortcut).split("+").map((part) => part.trim().toLowerCase());
  let key = "";
  let wantsCtrlOrCmd = false;
  let wantsShift = false;
  let wantsAlt = false;

  for (const part of parts) {
    if (part === "ctrl/cmd") {
      wantsCtrlOrCmd = true;
      continue;
    }
    if (part === "shift") {
      wantsShift = true;
      continue;
    }
    if (part === "alt" || part === "option" || part === "alt/option") {
      wantsAlt = true;
      continue;
    }
    key = part;
  }

  const hasCtrlOrCmd = event.ctrlKey || event.metaKey;
  if (wantsCtrlOrCmd !== hasCtrlOrCmd) {
    return false;
  }
  if (wantsShift !== Boolean(event.shiftKey)) {
    return false;
  }
  if (wantsAlt !== Boolean(event.altKey)) {
    return false;
  }

  return normalizeShortcutKey(event.key) === normalizeShortcutKey(key);
}

function normalizeShortcutKey(key) {
  if (!key) {
    return "";
  }
  return key.length === 1 ? key.toLowerCase() : key.toLowerCase();
}

function isEditableTarget(target) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  const tagName = target.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select";
}

function humanizeKebabLike(value) {
  return String(value)
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

async function fetchFixture(base, name) {
  return fetchJson(`${base}/api/dev/fixture/${encodeURIComponent(name)}`);
}

function normalizeBase(value) {
  return value.replace(/\/+$/, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
