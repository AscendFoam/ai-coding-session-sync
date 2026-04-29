const SCENARIOS = {
  conflict: {
    label: "Conflict",
    title: "Conflict Fixture Prototype",
    latestTitle: "Selection State",
    modes: {
      bundle: {
        label: "Aggregate bundle",
        files: [
          {
            key: "bundle",
            label: "sample-ui-bundle-conflict.json",
            path: "./sample-ui-bundle-conflict.json",
            type: "json",
          },
        ],
      },
      split: {
        label: "Split files",
        files: [
          {
            key: "latest",
            label: "sample-latest-conflict.json",
            path: "./sample-latest-conflict.json",
            type: "json",
          },
          {
            key: "manifest",
            label: "sample-manifest-conflict-selected.json",
            path: "./sample-manifest-conflict-selected.json",
            type: "json",
          },
          {
            key: "inspect",
            label: "sample-inspect-output-conflict-selected.json",
            path: "./sample-inspect-output-conflict-selected.json",
            type: "json",
          },
          {
            key: "handoff",
            label: "sample-handoff-conflict.md",
            path: "./sample-handoff-conflict.md",
            type: "text",
          },
        ],
      },
    },
  },
  dirty: {
    label: "Dirty",
    title: "Dirty Fixture Prototype",
    latestTitle: "Snapshot State",
    modes: {
      bundle: {
        label: "Aggregate bundle",
        files: [
          {
            key: "bundle",
            label: "sample-ui-bundle-dirty.json",
            path: "./sample-ui-bundle-dirty.json",
            type: "json",
          },
        ],
      },
      split: {
        label: "Split files",
        files: [
          {
            key: "latest",
            label: "sample-latest-pointer.json",
            path: "./sample-latest-pointer.json",
            type: "json",
          },
          {
            key: "manifest",
            label: "sample-manifest-dirty-selected.json",
            path: "./sample-manifest-dirty-selected.json",
            type: "json",
          },
          {
            key: "inspect",
            label: "sample-inspect-output-dirty-selected.json",
            path: "./sample-inspect-output-dirty-selected.json",
            type: "json",
          },
          {
            key: "handoff",
            label: "sample-handoff-dirty.md",
            path: "./sample-handoff-dirty.md",
            type: "text",
          },
        ],
      },
    },
  },
};

const state = {
  scenario: "conflict",
  mode: "bundle",
  viewModel: null,
  activeContextSessionId: null,
  loading: false,
};

const elements = {
  pageTitle: document.getElementById("pageTitle"),
  scenarioConflictButton: document.getElementById("scenarioConflictButton"),
  scenarioDirtyButton: document.getElementById("scenarioDirtyButton"),
  modeBundleButton: document.getElementById("modeBundleButton"),
  modeSplitButton: document.getElementById("modeSplitButton"),
  reloadButton: document.getElementById("reloadButton"),
  statusBanner: document.getElementById("statusBanner"),
  dataSourcePanel: document.getElementById("dataSourcePanel"),
  summaryGrid: document.getElementById("summaryGrid"),
  sourceList: document.getElementById("sourceList"),
  latestSectionTitle: document.getElementById("latestSectionTitle"),
  latestSelectionPanel: document.getElementById("latestSelectionPanel"),
  manifestPanel: document.getElementById("manifestPanel"),
  patchReplayPanel: document.getElementById("patchReplayPanel"),
  contextsPanel: document.getElementById("contextsPanel"),
  handoffPanel: document.getElementById("handoffPanel"),
  selectedExcerptsPanel: document.getElementById("selectedExcerptsPanel"),
  timelinePanel: document.getElementById("timelinePanel"),
};

init();

function init() {
  elements.scenarioConflictButton.addEventListener("click", () => loadScenario("conflict"));
  elements.scenarioDirtyButton.addEventListener("click", () => loadScenario("dirty"));
  elements.modeBundleButton.addEventListener("click", () => loadScenario(state.scenario, "bundle"));
  elements.modeSplitButton.addEventListener("click", () => loadScenario(state.scenario, "split"));
  elements.reloadButton.addEventListener("click", () => loadScenario(state.scenario, state.mode));

  const params = new URLSearchParams(window.location.search);
  const scenario = params.get("scenario");
  const mode = params.get("mode");

  if (scenario === "conflict" || scenario === "dirty") {
    state.scenario = scenario;
  }
  if (mode === "split" || mode === "bundle") {
    state.mode = mode;
  }

  if (!isModeSupported(state.scenario, state.mode)) {
    state.mode = "bundle";
  }

  loadScenario(state.scenario, state.mode);
}

async function loadScenario(scenario, requestedMode = "bundle") {
  const mode = isModeSupported(scenario, requestedMode) ? requestedMode : "bundle";
  state.loading = true;
  setActiveScenario(scenario);
  setActiveMode(scenario, mode);
  renderScenarioChrome(scenario);
  renderStatus(`Loading ${SCENARIOS[scenario].modes[mode].label.toLowerCase()}...`);

  try {
    const viewModel =
      scenario === "dirty"
        ? mode === "bundle"
          ? await loadDirtyBundleMode()
          : await loadDirtySplitMode()
        : mode === "bundle"
          ? await loadConflictBundleMode()
          : await loadConflictSplitMode();

    state.scenario = scenario;
    state.mode = mode;
    state.viewModel = viewModel;
    state.activeContextSessionId = pickInitialContext(viewModel);
    syncStateToUrl(scenario, mode);
    renderAll();
  } catch (error) {
    console.error(error);
    state.viewModel = null;
    renderError(error);
  } finally {
    state.loading = false;
  }
}

async function loadConflictBundleMode() {
  const payload = await fetchJson(SCENARIOS.conflict.modes.bundle.files[0].path);
  return {
    scenario: "conflict",
    scenarioLabel: SCENARIOS.conflict.label,
    mode: "bundle",
    modeLabel: SCENARIOS.conflict.modes.bundle.label,
    entry: payload.entry,
    latest: payload.latest,
    latestSelection: payload.latest_selection,
    manifest: payload.manifest,
    inspect: payload.inspect,
    handoff: payload.handoff,
    patchReplay: {
      available: true,
      data: payload.patch_replay,
      note: null,
    },
    sources: SCENARIOS.conflict.modes.bundle.files,
    notes: [
      "All conflict-state UI data is loaded from one bundle payload.",
    ],
  };
}

async function loadConflictSplitMode() {
  const [latest, manifest, inspect, handoffMarkdown] = await Promise.all([
    fetchJson(SCENARIOS.conflict.modes.split.files[0].path),
    fetchJson(SCENARIOS.conflict.modes.split.files[1].path),
    fetchJson(SCENARIOS.conflict.modes.split.files[2].path),
    fetchText(SCENARIOS.conflict.modes.split.files[3].path),
  ]);

  const context = manifest.source.contexts[0];
  const latestSelection = deriveLatestSelection(latest, manifest, inspect);

  return {
    scenario: "conflict",
    scenarioLabel: SCENARIOS.conflict.label,
    mode: "split",
    modeLabel: SCENARIOS.conflict.modes.split.label,
    entry: {
      project_id: manifest.project.id,
      active_tool: manifest.source.tool,
      available_tools: Object.keys(inspect),
      snapshot_id: manifest.snapshot_id,
      handoff_path: "handoffs/20260425T081500Z-sample-windows-codex.md",
    },
    latest,
    latestSelection,
    manifest,
    inspect,
    handoff: {
      path: "handoffs/20260425T081500Z-sample-windows-codex.md",
      format: "markdown",
      title: extractMarkdownTitle(handoffMarkdown),
      updated_at: manifest.created_at,
      current_goal: context.goal_candidate,
      summary: "Split-file conflict fixture set mirroring the selected candidate detail from the aggregate bundle.",
      markdown: handoffMarkdown,
    },
    patchReplay: {
      available: false,
      data: null,
      note: "This split-file fixture set does not include a patch_replay aggregate. Use bundle mode when prototyping the doctor panel command flow.",
    },
    sources: SCENARIOS.conflict.modes.split.files,
    notes: [
      "The selected manifest fixture mirrors the currently loaded recommended candidate detail.",
      "The inspect fixture still includes the older Mac candidate for ranking and compare-state UI.",
    ],
  };
}

async function loadDirtyBundleMode() {
  const payload = await fetchJson(SCENARIOS.dirty.modes.bundle.files[0].path);
  return {
    scenario: "dirty",
    scenarioLabel: SCENARIOS.dirty.label,
    mode: "bundle",
    modeLabel: SCENARIOS.dirty.modes.bundle.label,
    entry: payload.entry,
    latest: payload.latest,
    latestSelection: payload.latest_selection,
    manifest: payload.manifest,
    inspect: payload.inspect,
    handoff: payload.handoff,
    patchReplay: {
      available: true,
      data: payload.patch_replay,
      note: null,
    },
    sources: SCENARIOS.dirty.modes.bundle.files,
    notes: [
      "Dirty-state UI data is loaded from one bundle payload.",
      "This path includes structured patch replay guidance and warning metadata in one request.",
    ],
  };
}

async function loadDirtySplitMode() {
  const [latest, manifest, inspect, handoffMarkdown] = await Promise.all([
    fetchJson(SCENARIOS.dirty.modes.split.files[0].path),
    fetchJson(SCENARIOS.dirty.modes.split.files[1].path),
    fetchJson(SCENARIOS.dirty.modes.split.files[2].path),
    fetchText(SCENARIOS.dirty.modes.split.files[3].path),
  ]);

  const context = manifest.source.contexts[0];
  const latestSelection = deriveLatestSelection(latest, manifest, inspect);

  return {
    scenario: "dirty",
    scenarioLabel: SCENARIOS.dirty.label,
    mode: "split",
    modeLabel: SCENARIOS.dirty.modes.split.label,
    entry: {
      project_id: manifest.project.id,
      active_tool: manifest.source.tool,
      available_tools: Object.keys(inspect),
      snapshot_id: manifest.snapshot_id,
      handoff_path: "handoffs/20260425T081500Z-sample-windows-claude.md",
    },
    latest,
    latestSelection,
    manifest,
    inspect,
    handoff: {
      path: "handoffs/20260425T081500Z-sample-windows-claude.md",
      format: "markdown",
      title: extractMarkdownTitle(handoffMarkdown),
      updated_at: manifest.created_at,
      current_goal: context.goal_candidate,
      summary: "Split-file dirty fixture set mirroring the selected dirty-state detail from the aggregate bundle.",
      markdown: handoffMarkdown,
    },
    patchReplay: {
      available: false,
      data: null,
      note: "This split-file dirty fixture set does not include a patch_replay aggregate. Use bundle mode when you need the doctor panel command flow.",
    },
    sources: SCENARIOS.dirty.modes.split.files,
    notes: [
      "The selected manifest fixture mirrors the dirty-state detail currently embedded in the aggregate bundle.",
      "The split inspect fixture stays focused on the primary selected Claude session while preserving compare indexes.",
    ],
  };
}

function deriveLatestSelection(latest, manifest, inspect) {
  if ("snapshot_id" in latest) {
    return {
      state: "resolved",
      active_snapshot_id: latest.snapshot_id,
      candidates: [latest.snapshot_id],
      recommended_snapshot_id: latest.snapshot_id,
      recommended_reason: "Only one latest snapshot is active.",
      derived: true,
    };
  }

  const alternateCount = (inspect[manifest.source.tool] || []).length - 1;
  return {
    state: "requires-selection",
    active_snapshot_id: null,
    candidates: latest.candidates,
    recommended_snapshot_id: manifest.snapshot_id,
    recommended_reason:
      alternateCount > 0
        ? "Derived from the selected conflict manifest fixture that ships with the higher-ranked candidate detail."
        : "Derived from the selected conflict manifest fixture.",
    derived: true,
  };
}

function pickInitialContext(viewModel) {
  const toolContexts = getToolContexts(viewModel);
  const primarySessionId = viewModel.manifest.source.contexts[0]?.session_id;
  const matching = toolContexts.find((context) => context.session_id === primarySessionId);
  return (matching || toolContexts[0] || {}).session_id || null;
}

function renderAll() {
  if (!state.viewModel) {
    return;
  }

  setActiveMode(state.mode);
  renderStatus(`${state.viewModel.modeLabel} loaded`);
  renderDataSourcePanel();
  renderSummary();
  renderSourceList();
  renderLatestSelection();
  renderManifest();
  renderPatchReplay();
  renderContexts();
  renderHandoff();
  renderCompare();
}

function renderStatus(message) {
  elements.statusBanner.textContent = message;
}

function renderError(error) {
  renderStatus("Failed to load fixtures");
  elements.dataSourcePanel.innerHTML = "";
  elements.summaryGrid.innerHTML = `<div class="empty-card">Unable to load prototype data: ${escapeHtml(error.message)}</div>`;
  elements.sourceList.innerHTML = "";
  elements.latestSelectionPanel.innerHTML = "";
  elements.manifestPanel.innerHTML = "";
  elements.patchReplayPanel.innerHTML = "";
  elements.contextsPanel.innerHTML = "";
  elements.handoffPanel.innerHTML = "";
  elements.selectedExcerptsPanel.innerHTML = "";
  elements.timelinePanel.innerHTML = "";
}

function setActiveScenario(scenario) {
  const isConflict = scenario === "conflict";
  elements.scenarioConflictButton.classList.toggle("is-active", isConflict);
  elements.scenarioDirtyButton.classList.toggle("is-active", !isConflict);
  elements.scenarioConflictButton.setAttribute("aria-selected", String(isConflict));
  elements.scenarioDirtyButton.setAttribute("aria-selected", String(!isConflict));
}

function setActiveMode(scenario, mode) {
  const isBundle = mode === "bundle";
  elements.modeBundleButton.classList.toggle("is-active", isBundle);
  elements.modeSplitButton.classList.toggle("is-active", !isBundle);
  elements.modeBundleButton.setAttribute("aria-selected", String(isBundle));
  elements.modeSplitButton.setAttribute("aria-selected", String(!isBundle));
  const splitSupported = isModeSupported(scenario, "split");
  elements.modeSplitButton.disabled = !splitSupported;
  elements.modeSplitButton.title = splitSupported ? "" : "Split fixtures are not available for this scenario.";
}

function renderScenarioChrome(scenario) {
  const config = SCENARIOS[scenario];
  elements.pageTitle.textContent = config.title;
  elements.latestSectionTitle.textContent = config.latestTitle;
  document.title = `AI Session Sync ${config.label} Prototype`;
}

function syncStateToUrl(scenario, mode) {
  const url = new URL(window.location.href);
  url.searchParams.set("scenario", scenario);
  url.searchParams.set("mode", mode);
  window.history.replaceState({}, "", url);
}

function renderSummary() {
  const { viewModel } = state;
  const latestSelection = viewModel.latestSelection;
  const patchReplay = viewModel.patchReplay;
  const summaryCards = [
    {
      label: "Scenario",
      value: viewModel.scenarioLabel,
      note: viewModel.scenario === "conflict" ? "Latest conflict and candidate resolution" : "Dirty worktree, patch, and warning state",
    },
    {
      label: "Mode",
      value: viewModel.modeLabel,
      note: viewModel.mode === "bundle" ? "Single fetch" : "Four-file load",
    },
    {
      label: "Latest State",
      value: latestSelection.state,
      note:
        latestSelection.state === "requires-selection"
          ? `${latestSelection.candidates.length} candidate snapshots`
          : "Current pointer is already resolved",
    },
    {
      label: "Loaded Snapshot",
      value: viewModel.manifest.snapshot_id,
      note: `${viewModel.manifest.project.branch} @ ${viewModel.manifest.project.head}`,
    },
    {
      label: "Patch Replay",
      value: patchReplay.available ? patchReplay.data.recommended_mode : "aggregate only",
      note: patchReplay.available
        ? patchReplay.data.recommended_reason
        : "No structured replay aggregate in split fixtures",
    },
  ];

  elements.summaryGrid.innerHTML = summaryCards
    .map(
      (card) => `
        <div class="metric">
          <div class="metric-label">${escapeHtml(card.label)}</div>
          <div class="metric-value">${escapeHtml(card.value)}</div>
          <div class="metric-note">${escapeHtml(card.note)}</div>
        </div>
      `
    )
    .join("");
}

function renderDataSourcePanel() {
  const { viewModel } = state;
  const loadedFixtures = viewModel.sources
    .map(
      (source) => `
        <div class="fixture-item">
          <div class="fixture-meta">
            <div class="fixture-name">${escapeHtml(source.label)}</div>
            <div class="fixture-kind">${escapeHtml(source.type)}</div>
          </div>
          <a class="source-link" href="${source.path}" target="_blank" rel="noreferrer">Open</a>
        </div>
      `
    )
    .join("");

  const aggregates = getAggregateAvailability(viewModel)
    .map(
      (aggregate) => `
        <div class="aggregate-row">
          <div class="aggregate-head">
            <div class="aggregate-name">${escapeHtml(aggregate.name)}</div>
            ${statusTag(aggregate.stateLabel, aggregate.tone)}
          </div>
          <div class="aggregate-note">${escapeHtml(aggregate.note)}</div>
        </div>
      `
    )
    .join("");

  const differences = getPathDifferences(viewModel)
    .map(
      (difference) => `
        <div class="diff-row">
          <div class="diff-head">
            <div class="diff-name">${escapeHtml(difference.name)}</div>
            ${statusTag(difference.badge, difference.tone)}
          </div>
          <div class="diff-note">${escapeHtml(difference.note)}</div>
        </div>
      `
    )
    .join("");

  const provenance = getFieldProvenance(viewModel)
    .map(
      (item) => `
        <div class="provenance-row">
          <div class="provenance-head">
            <div class="provenance-name">${escapeHtml(item.name)}</div>
            ${statusTag(item.badge, item.tone)}
          </div>
          <div class="provenance-note">${escapeHtml(item.note)}</div>
        </div>
      `
    )
    .join("");

  elements.dataSourcePanel.innerHTML = `
    <div class="data-panel-card">
      <div class="data-panel-title">Loaded Fixtures</div>
      <div class="data-panel-copy">
        ${escapeHtml(viewModel.scenarioLabel)} scenario via ${escapeHtml(viewModel.modeLabel.toLowerCase())}.
      </div>
      <div class="fixture-list">${loadedFixtures}</div>
    </div>
    <div class="data-panel-card">
      <div class="data-panel-title">Aggregate Availability</div>
      <div class="data-panel-copy">Which convenience blocks are present as first-class payloads on this path.</div>
      <div class="aggregate-list">${aggregates}</div>
    </div>
    <div class="data-panel-card">
      <div class="data-panel-title">Bundle vs Split</div>
      <div class="data-panel-copy">What changes when the frontend switches contract paths for this scenario.</div>
      <div class="diff-list">${differences}</div>
    </div>
    <div class="data-panel-card">
      <div class="data-panel-title">Field Provenance</div>
      <div class="data-panel-copy">Which values come straight from fixtures and which ones are frontend convenience derivations.</div>
      <div class="provenance-list">${provenance}</div>
    </div>
  `;
}

function renderSourceList() {
  const { viewModel } = state;
  const sourceLinks = viewModel.sources
    .map(
      (source) => `
        <a class="source-link" href="${source.path}" target="_blank" rel="noreferrer">
          ${escapeHtml(source.label)}
        </a>
      `
    )
    .join("");

  const notes = (viewModel.notes || [])
    .map((note) => `<div class="source-line">${escapeHtml(note)}</div>`)
    .join("");

  elements.sourceList.innerHTML = `
    <div class="source-line">
      <strong>Fixtures</strong>
      <div class="source-links">${sourceLinks}</div>
    </div>
    ${notes}
  `;
}

function renderLatestSelection() {
  const { viewModel } = state;
  const latestSelection = viewModel.latestSelection;
  const loadedSnapshotId = viewModel.manifest.snapshot_id;

  const cards = latestSelection.candidates.map((candidateId) => {
    const tags = [];
    if (candidateId === latestSelection.recommended_snapshot_id) {
      tags.push(statusTag("Recommended", "accent"));
    }
    if (candidateId === loadedSnapshotId) {
      tags.push(statusTag("Loaded detail", "ok"));
    }

    return `
      <div class="candidate-card">
        <div class="candidate-title-row">
          <div class="candidate-title">${escapeHtml(shortSnapshot(candidateId))}</div>
          ${statusTag(latestSelection.state, latestSelection.state === "resolved" ? "ok" : "warn")}
        </div>
        <div class="candidate-subtitle">${escapeHtml(candidateId)}</div>
        <div class="tag-row">${tags.join("")}</div>
      </div>
    `;
  });

  const recommendation = latestSelection.recommended_reason
    ? `<div class="muted-text">${escapeHtml(latestSelection.recommended_reason)}</div>`
    : "";

  const scenarioNote =
    viewModel.scenario === "dirty"
      ? `<div class="muted-text">Dirty mode uses a resolved latest snapshot so the UI can focus on patch replay, warnings, and provenance competition.</div>`
      : "";

  elements.latestSelectionPanel.innerHTML = cards.join("") + recommendation + scenarioNote;
}

function renderManifest() {
  const { manifest } = state.viewModel;
  const context = manifest.source.contexts[0];
  const warnings = manifest.redaction.warnings.length
    ? `
      <div class="panel-title">Warnings</div>
      <ul class="warning-list">
        ${manifest.redaction.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}
      </ul>
    `
    : `<div class="muted-text">No redaction warnings in this fixture.</div>`;

  elements.manifestPanel.innerHTML = `
    <div class="candidate-card">
      <div class="candidate-title-row">
        <div>
          <div class="candidate-title">${escapeHtml(manifest.project.id)}</div>
          <div class="candidate-subtitle">${escapeHtml(manifest.project.git_remote)}</div>
        </div>
        ${statusTag(manifest.project.dirty ? "dirty" : "clean", manifest.project.dirty ? "warn" : "ok")}
      </div>
      <div class="metric-grid">
        ${metricCell("Snapshot", manifest.snapshot_id)}
        ${metricCell("Tool", manifest.source.tool)}
        ${metricCell("Branch", manifest.project.branch)}
        ${metricCell("HEAD", manifest.project.head)}
        ${metricCell("Device", manifest.source.device_id)}
        ${metricCell("Patch", manifest.artifacts.patch || "(none)")}
      </div>
      <div class="panel-title" style="margin-top:14px;">Current Goal</div>
      <div>${escapeHtml(context.goal_candidate)}</div>
      <ul class="reason-list">
        ${context.score_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
      </ul>
      ${warnings}
    </div>
  `;
}

function renderPatchReplay() {
  const patchReplay = state.viewModel.patchReplay;

  if (!patchReplay.available) {
    elements.patchReplayPanel.innerHTML = `
      <div class="empty-card">
        <div class="panel-title">No Structured Replay Aggregate</div>
        <div class="muted-text">${escapeHtml(patchReplay.note)}</div>
        <div class="metric-grid" style="margin-top:14px;">
          ${metricCell("Patch Artifact", state.viewModel.manifest.artifacts.patch || "(none)")}
          ${metricCell("Loaded Mode", state.viewModel.modeLabel)}
        </div>
      </div>
    `;
    return;
  }

  const replay = patchReplay.data;
  elements.patchReplayPanel.innerHTML = `
    <div class="candidate-card">
      <div class="candidate-title-row">
        <div>
          <div class="candidate-title">${escapeHtml(replay.recommended_mode)}</div>
          <div class="candidate-subtitle">${escapeHtml(replay.recommended_reason)}</div>
        </div>
        ${statusTag(replay.state, replay.state === "blocked" ? "warn" : "ok")}
      </div>
      <div class="metric-grid">
        ${metricCell("Plain Apply", replay.plain_apply_state)}
        ${metricCell("3-Way", replay.three_way_state)}
        ${metricCell("Patch", replay.patch_path || "(none)")}
        ${metricCell("Command Mode", replay.recommended_mode || "(none)")}
      </div>
      <div class="command-block">
        <code>${escapeHtml(replay.recommended_command || "No replay command")}</code>
      </div>
    </div>
  `;
}

function renderContexts() {
  const contexts = getToolContexts(state.viewModel);
  const loadedSessionId = state.viewModel.manifest.source.contexts[0]?.session_id;

  elements.contextsPanel.innerHTML = contexts
    .map((context, index) => {
      const active = context.session_id === state.activeContextSessionId;
      const tags = [
        statusTag(`#${index + 1}`, "neutral"),
        statusTag(`score ${context.score}`, "accent"),
      ];
      if (context.session_id === loadedSessionId) {
        tags.push(statusTag("Loaded detail", "ok"));
      } else if (state.viewModel.scenario === "conflict") {
        tags.push(statusTag("Alternate", "warn"));
      } else {
        tags.push(statusTag("Ranked candidate", "warn"));
      }

      return `
        <button
          type="button"
          class="context-card ${active ? "is-active" : ""}"
          data-session-id="${context.session_id}"
          aria-pressed="${active ? "true" : "false"}"
        >
          <div class="context-title-row">
            <div>
              <div class="context-title">${escapeHtml(context.title)}</div>
              <div class="context-subtitle">${escapeHtml(context.goal_candidate)}</div>
            </div>
          </div>
          <div class="tag-row">${tags.join("")}</div>
          <div class="metric-grid">
            ${metricCell("Selected Excerpts", String(context.excerpt_count))}
            ${metricCell("Total Excerpts", String(context.total_excerpt_count))}
            ${metricCell("Users", String(context.total_user_count))}
            ${metricCell("Assistants", String(context.total_assistant_count))}
          </div>
        </button>
      `;
    })
    .join("");

  Array.from(elements.contextsPanel.querySelectorAll(".context-card")).forEach((button) => {
    button.addEventListener("click", () => {
      state.activeContextSessionId = button.dataset.sessionId;
      renderContexts();
      renderCompare();
    });
  });
}

function renderHandoff() {
  elements.handoffPanel.innerHTML = renderMarkdown(state.viewModel.handoff.markdown);
}

function renderCompare() {
  const context = getActiveContext();
  if (!context) {
    elements.selectedExcerptsPanel.innerHTML = `<div class="empty-card">No context available.</div>`;
    elements.timelinePanel.innerHTML = `<div class="empty-card">No excerpts available.</div>`;
    return;
  }

  elements.selectedExcerptsPanel.innerHTML = context.excerpts
    .map(
      (excerpt) => `
        <div class="excerpt-card">
          <div class="timeline-head">
            <div class="context-title">${escapeHtml(excerpt.role)}</div>
            ${statusTag(`#${excerpt.selected_index}`, "accent")}
          </div>
          <div class="timeline-meta">${escapeHtml(excerpt.created_at)}</div>
          <div class="excerpt-text">${escapeHtml(excerpt.text)}</div>
        </div>
      `
    )
    .join("");

  elements.timelinePanel.innerHTML = context.all_excerpts
    .map(
      (excerpt, index) => `
        <div class="timeline-entry ${excerpt.selected ? "is-selected" : ""}">
          <div class="timeline-head">
            <div class="context-title">${escapeHtml(excerpt.role)}</div>
            <div class="tag-row">
              ${statusTag(`#${index + 1}`, "neutral")}
              ${excerpt.selected ? statusTag(`selected ${excerpt.selected_index}`, "accent") : statusTag("trimmed", "neutral")}
            </div>
          </div>
          <div class="timeline-meta">${escapeHtml(excerpt.created_at)}</div>
          <div class="timeline-text">${escapeHtml(excerpt.text)}</div>
        </div>
      `
    )
    .join("");
}

function getToolContexts(viewModel) {
  return viewModel.inspect[viewModel.manifest.source.tool] || [];
}

function getActiveContext() {
  return getToolContexts(state.viewModel).find((context) => context.session_id === state.activeContextSessionId) || null;
}

function metricCell(label, value) {
  return `
    <div class="metric-cell">
      <div class="label">${escapeHtml(label)}</div>
      <div class="value">${escapeHtml(value)}</div>
    </div>
  `;
}

function shortSnapshot(snapshotId) {
  const match = snapshotId.match(/^([0-9]{8}T[0-9]{6}Z)-(.+)$/);
  if (!match) {
    return snapshotId;
  }
  return `${match[1]} / ${match[2]}`;
}

function statusTag(label, tone) {
  return `<span class="status-tag status-${tone}">${escapeHtml(label)}</span>`;
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.text();
}

function extractMarkdownTitle(markdown) {
  const line = markdown.split("\n").find((entry) => entry.startsWith("# "));
  return line ? line.replace(/^#\s+/, "").trim() : "Handoff";
}

function renderMarkdown(markdown) {
  const lines = markdown.split("\n");
  const html = [];
  let listType = null;

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }

    if (/^###\s+/.test(trimmed)) {
      closeList();
      html.push(`<h3>${renderInline(trimmed.replace(/^###\s+/, ""))}</h3>`);
      continue;
    }

    if (/^##\s+/.test(trimmed)) {
      closeList();
      html.push(`<h2>${renderInline(trimmed.replace(/^##\s+/, ""))}</h2>`);
      continue;
    }

    if (/^#\s+/.test(trimmed)) {
      closeList();
      html.push(`<h1>${renderInline(trimmed.replace(/^#\s+/, ""))}</h1>`);
      continue;
    }

    if (/^- /.test(trimmed)) {
      if (listType !== "ul") {
        closeList();
        listType = "ul";
        html.push("<ul>");
      }
      html.push(`<li>${renderInline(trimmed.replace(/^- /, ""))}</li>`);
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      if (listType !== "ol") {
        closeList();
        listType = "ol";
        html.push("<ol>");
      }
      html.push(`<li>${renderInline(trimmed.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInline(trimmed)}</p>`);
  }

  closeList();
  return html.join("");
}

function renderInline(text) {
  return text
    .split(/(`[^`]+`)/g)
    .map((part) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return `<code>${escapeHtml(part.slice(1, -1))}</code>`;
      }
      return escapeHtml(part);
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isModeSupported(scenario, mode) {
  return Boolean(SCENARIOS[scenario]?.modes?.[mode]);
}

function getAggregateAvailability(viewModel) {
  return [
    {
      name: "latest_selection",
      stateLabel: viewModel.latestSelection ? "present" : "missing",
      tone: viewModel.latestSelection ? "ok" : "danger",
      note: viewModel.latestSelection
        ? "The UI can render selection state without inferring from raw latest files."
        : "The UI would need to derive selection state itself.",
    },
    {
      name: "patch_replay",
      stateLabel: viewModel.patchReplay.available ? "present" : "missing",
      tone: viewModel.patchReplay.available ? "ok" : "warn",
      note: viewModel.patchReplay.available
        ? "Structured replay guidance is available as a dedicated aggregate."
        : viewModel.patchReplay.note,
    },
    {
      name: "handoff summary",
      stateLabel: viewModel.handoff.summary ? "present" : "derived",
      tone: viewModel.handoff.summary ? "ok" : "accent",
      note: viewModel.handoff.summary
        ? "Short operator-facing summary is available alongside markdown."
        : "Only raw markdown is available on this path.",
    },
  ];
}

function getPathDifferences(viewModel) {
  const differences = [];

  if (viewModel.mode === "bundle") {
    differences.push({
      name: "Network shape",
      badge: "single request",
      tone: "ok",
      note: "The page gets latest, manifest, inspect, handoff, and patch replay from one payload.",
    });
    differences.push({
      name: "Replay guidance",
      badge: viewModel.patchReplay.available ? "direct aggregate" : "n/a",
      tone: viewModel.patchReplay.available ? "ok" : "warn",
      note: viewModel.patchReplay.available
        ? "Doctor-style replay suggestions are renderable without frontend stitching."
        : "This bundle path does not expose structured replay guidance.",
    });
  } else {
    differences.push({
      name: "Network shape",
      badge: `${viewModel.sources.length} files`,
      tone: "accent",
      note: "The frontend reconstructs the page from separate latest, manifest, inspect, and handoff fixtures.",
    });
    differences.push({
      name: "Replay guidance",
      badge: "missing aggregate",
      tone: "warn",
      note: "Patch replay is intentionally absent here, so the UI can exercise a degraded but explicit contract path.",
    });
  }

  differences.push({
    name: "Current scenario focus",
    badge: viewModel.scenario === "conflict" ? "selection" : "warnings",
    tone: viewModel.scenario === "conflict" ? "accent" : "warn",
    note:
      viewModel.scenario === "conflict"
        ? "This path emphasizes latest resolution, recommended candidate detail, and candidate comparison."
        : "This path emphasizes dirty worktree state, warnings, ranked contexts, and patch-aware operator guidance.",
  });

  return differences;
}

function getFieldProvenance(viewModel) {
  const items = [
    {
      name: "manifest",
      badge: "source-of-truth",
      tone: "ok",
      note: "Loaded directly from a fixture file or bundle payload and should be treated as backend contract data.",
    },
    {
      name: "inspect",
      badge: "source-of-truth",
      tone: "ok",
      note: "Rendered from the fixture payload as-is, including compare indexes and ranking metadata.",
    },
    {
      name: "latest_selection",
      badge: viewModel.latestSelection?.derived ? "derived" : "source-of-truth",
      tone: viewModel.latestSelection?.derived ? "accent" : "ok",
      note: viewModel.latestSelection?.derived
        ? "Frontend convenience layer built from split latest + manifest + inspect so the UI can use one selection model."
        : "Provided directly by the bundled fixture as an explicit convenience aggregate.",
    },
    {
      name: "patch_replay",
      badge: viewModel.patchReplay.available ? "source-of-truth" : "missing",
      tone: viewModel.patchReplay.available ? "ok" : "warn",
      note: viewModel.patchReplay.available
        ? "Structured replay guidance comes directly from the payload."
        : "No replay aggregate exists on this path, so the UI must either omit the panel or render a degraded placeholder.",
    },
    {
      name: "handoff.summary",
      badge: viewModel.mode === "bundle" ? "source-of-truth" : "derived",
      tone: viewModel.mode === "bundle" ? "ok" : "accent",
      note:
        viewModel.mode === "bundle"
          ? "Short summary is part of the backend payload."
          : "Summary is synthesized by the prototype to keep split mode aligned with the bundle view.",
    },
  ];

  return items;
}
