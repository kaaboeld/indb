<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import {
  IndbApiClient,
  clusterNodes,
  defaultApiBase,
} from "./api/client";
import DataTable from "./components/DataTable.vue";
import JsonOutput from "./components/JsonOutput.vue";
import SelectField from "./components/SelectField.vue";
import StatCard from "./components/StatCard.vue";
import TabBar from "./components/TabBar.vue";
import { QUERY_MODES, type TabId } from "./types";
import {
  eventContent,
  eventIdShort,
  formatTimestamp,
  locationLabel,
  moduleStatusClass,
  nodeStatusClass,
  prettyJson,
  truncate,
} from "./utils/format";

const WUI_BUILD = "2026-07-11";

const storedBase = localStorage.getItem("indb_api_url") ?? defaultApiBase();
const apiBaseInput = ref(storedBase);
const apiBase = ref(storedBase);
const activeTab = ref<TabId>("control");
const loading = ref(false);
const loadingMsg = ref("");
const logLines = ref<string[]>([]);
const lastRefresh = ref<Date | null>(null);

const api = computed(() => new IndbApiClient(apiBase.value));

// Control
const eventsCount = ref("—");
const fusionRate = ref("—");
const serverStatus = ref("—");
const serverTone = ref<"default" | "ok" | "warn" | "err">("default");
const sysLine = ref("");

// Events
const eventRows = ref<string[][]>([]);
const eventStatus = ref("Loading…");
const eventFilter = ref("");
const eventSource = ref("mixed");
const sourceOptions = ref<{ label: string; value: string }[]>([
  { label: "All sources", value: "mixed" },
  { label: "Latest", value: "latest" },
]);
const eventsCache = ref<Record<string, unknown>[]>([]);

// Modules
const moduleRows = ref<string[][]>([]);
const protocolRows = ref<string[][]>([]);
const modulesStatus = ref("");

// Cluster
const clusterRows = ref<string[][]>([]);
const clusterSummary = ref("Loading…");

// Query
const queryMode = ref("interpret");
const queryPrimary = ref("");
const querySecondary = ref("");
const queryTertiary = ref("");
const queryOutput = ref("");
const queryHint = computed(
  () => QUERY_MODES.find((m) => m.key === queryMode.value)?.hint ?? "",
);

// Analytics
const analyticsStats = ref({
  health: "—",
  locations: "—",
  tokens: "—",
  fusion: "—",
  ws: "—",
});
const insights = ref<string[]>([]);
const analyticsDetail = ref("");

let pollTimer: ReturnType<typeof setInterval> | null = null;

function pushLog(line: string) {
  const ts = new Date().toLocaleTimeString();
  logLines.value = [...logLines.value.slice(-200), `[${ts}] ${line}`];
}

function applyApiBase() {
  apiBase.value = apiBaseInput.value.trim();
  localStorage.setItem("indb_api_url", apiBase.value);
  pushLog(`API → ${apiBase.value || window.location.origin}`);
  refreshAll();
}

async function withLoading<T>(label: string, fn: () => Promise<T>): Promise<T> {
  loading.value = true;
  loadingMsg.value = label;
  try {
    return await fn();
  } finally {
    loading.value = false;
    loadingMsg.value = "";
    lastRefresh.value = new Date();
  }
}

async function refreshControl() {
  const client = api.value;
  const [overview, health] = await Promise.all([
    client.analyticsOverview(),
    client.health(),
  ]);
  const db = (overview.database ?? {}) as Record<string, unknown>;
  const perf = (overview.performance ?? {}) as Record<string, unknown>;
  const fusionOverview = (overview.fusion ?? {}) as Record<string, unknown>;

  if (health.status === "ok") {
    eventsCount.value = String(db.total_events ?? 0);
    serverStatus.value = "Running";
    serverTone.value = "ok";
  } else {
    eventsCount.value = "—";
    serverStatus.value = "Down";
    serverTone.value = "err";
    pushLog(`API error: ${health.error ?? client.lastError ?? "unreachable"}`);
  }

  let fusion = perf.fusion_compression_rate ?? fusionOverview.fusion_rate ?? "—";
  fusionRate.value = typeof fusion === "number" ? `${fusion}%` : String(fusion);

  const sys = (overview.system_health ?? {}) as Record<string, unknown>;
  if (sys.cpu_percent != null) {
    sysLine.value = `CPU ${Number(sys.cpu_percent).toFixed(1)}% · RAM ${Number(sys.memory_rss_mb ?? 0).toFixed(0)} MB`;
  }
}

async function refreshSourceOptions() {
  const overview = await api.value.analyticsOverview();
  const top = (overview.database as Record<string, unknown> | undefined)
    ?.top_locations as Record<string, number> | undefined;
  const opts = [
    { label: "All sources", value: "mixed" },
    { label: "Latest", value: "latest" },
  ];
  if (top) {
    for (const loc of Object.keys(top)) {
      opts.push({ label: locationLabel(loc, 30), value: loc });
    }
  }
  sourceOptions.value = opts;
}

function renderEvents(list: Record<string, unknown>[], label: string) {
  const q = eventFilter.value.trim().toLowerCase();
  const filtered = q
    ? list.filter((e) => JSON.stringify(e).toLowerCase().includes(q))
    : list;
  eventRows.value = filtered.map((e) => {
    const fused = Number(e.fusion_count ?? 0) > 0 || Boolean(e.is_fused);
    return [
      `${fused ? "⚡ " : ""}${eventIdShort(e)}`,
      formatTimestamp(Number(e.timestamp ?? 0)),
      locationLabel(String(e.location ?? "—")),
      truncate(eventContent(e), 72),
    ];
  });
  const sources = new Set(filtered.map((e) => String(e.location ?? "—")));
  eventStatus.value = `${filtered.length} events · ${label} · ${sources.size} sources`;
}

async function refreshEvents() {
  await refreshSourceOptions();
  const client = api.value;
  let events: Record<string, unknown>[] = [];
  let label = eventSource.value;
  if (eventSource.value === "mixed") {
    events = await client.eventsMixed(10, 50);
    label = "mixed sources";
  } else if (eventSource.value === "latest") {
    events = await client.events(50);
    label = "latest";
  } else {
    events = await client.events(50, {
      filter_key: "location",
      filter_value: eventSource.value,
    });
    label = locationLabel(eventSource.value, 30);
  }
  eventsCache.value = events;
  renderEvents(events, label);
}

async function searchEvents() {
  const q = eventFilter.value.trim();
  if (!q) {
    renderEvents(eventsCache.value, eventSource.value);
    return;
  }
  const results = await api.value.search(q, 50);
  renderEvents(results, `search: ${q}`);
}

async function refreshModules() {
  const [modules, protocols] = await Promise.all([
    api.value.modules(),
    api.value.protocols(),
  ]);
  moduleRows.value = modules.map((m) => [
    String(m.name ?? "?"),
    m.enabled ? "✓" : "✗",
    String(m.status ?? "unknown"),
    m.needs_api_key ? (m.has_api_key ? "✓" : "✗") : "—",
  ]);
  const protoList = (protocols.protocols ?? []) as Record<string, unknown>[];
  protocolRows.value = protoList.map((p) => [
    String(p.name ?? "?"),
    String(p.status ?? "—"),
    String(p.port ?? "—"),
  ]);
  modulesStatus.value = `Protocols: ${protocols.status ?? "unknown"} · ${protoList.length} registered`;
}

async function refreshCluster() {
  const client = api.value;
  const raft = await client.raftStatus();
  const nodes = clusterNodes(apiBase.value || window.location.origin);
  let active = 0;
  const rows: string[][] = [];
  for (const node of nodes) {
    const { ok, data } = await client.nodeStatus(node.url);
    if (ok) active += 1;
    const nodeRaft = (data.raft ?? {}) as Record<string, unknown>;
    const state = String(
      nodeRaft.state ?? nodeRaft.status ?? raft.status ?? "—",
    );
    const isLeader = state.toLowerCase() === "leader";
    rows.push([
      node.name,
      ok ? "UP" : "DOWN",
      node.port,
      isLeader ? `★ ${state}` : state,
      String(nodeRaft.term ?? raft.term ?? "—"),
    ]);
  }
  clusterRows.value = rows;
  const strategy = String(raft.status ?? (active ? "active" : "unreachable"));
  clusterSummary.value = `Endpoints ${active}/${nodes.length} up · Raft ${strategy}`;
}

async function refreshAnalytics() {
  const client = api.value;
  const [overview, fusion, insightList, ws] = await Promise.all([
    client.analyticsOverview(),
    client.fusionStats(),
    client.analyticsInsights(),
    client.websocketStats(),
  ]);
  const db = (overview.database ?? {}) as Record<string, unknown>;
  const tokens = (overview.tokens ?? {}) as Record<string, unknown>;
  const fusionOverview = (overview.fusion ?? {}) as Record<string, unknown>;
  let fusionVal = fusionOverview.fusion_rate ?? "—";
  const metrics = (fusion.metrics ?? {}) as Record<string, unknown>;
  if (metrics.fusion_rate != null) fusionVal = metrics.fusion_rate;

  analyticsStats.value = {
    health: String(overview.health_score ?? "—"),
    locations: String(db.unique_locations ?? "—"),
    tokens: String(tokens.unique_tokens ?? tokens.total_tokens ?? "—"),
    fusion: `${fusionVal}%`,
    ws: String(ws.active_connections ?? ws.connections ?? "—"),
  };
  insights.value = insightList.slice(0, 6);
  const sections: Record<string, unknown> = {
    Database: db,
    Fusion: fusionOverview,
    "Fusion Stats": fusion,
    Temporal: overview.temporal,
    Performance: overview.performance,
    Cognitive: overview.cognitive,
    WebSocket: ws,
  };
  analyticsDetail.value = Object.entries(sections)
    .filter(([, v]) => v && Object.keys(v as object).length)
    .map(([title, data]) => `══ ${title} ══\n${prettyJson(data, 1500)}`)
    .join("\n\n");
}

async function runQuery() {
  const client = api.value;
  const mode = queryMode.value;
  const p = queryPrimary.value.trim();
  const s = querySecondary.value.trim();
  const t = queryTertiary.value.trim();
  queryOutput.value = `▶ ${mode}: ${p || "(empty)"}\n`;
  try {
    let result: unknown;
    const split = (v: string, n = 2) =>
      v.split("|", n).map((x) => x.trim());

    switch (mode) {
      case "interpret": {
        const parts = split(p, 3);
        const mood = parts[0];
        const location = parts[1] ?? "";
        const goal = parts[2] ?? s;
        if (!mood || !location) throw new Error("mood and location required");
        result = await client.interpret(mood, location, goal);
        break;
      }
      case "prism":
        if (!p) throw new Error("query required");
        result = await client.prismSynthesize(p);
        break;
      case "instinct": {
        const parts = p.split("|");
        const q = parts[0]?.trim() ?? "";
        const ad = parts[1]?.trim() || s;
        if (!q || !ad) throw new Error("query and adrenaline required");
        result = await client.prismInstinct(q, parseFloat(ad));
        break;
      }
      case "lens": {
        const parts = split(p);
        const a = parts[0];
        const b = parts[1] ?? s;
        if (!a || !b) throw new Error("both contexts required");
        result = await client.lensQuery(a, b);
        break;
      }
      case "echo": {
        const seed = p || s;
        if (!seed) throw new Error("seed UUID required");
        result = await client.echoResonate(seed);
        break;
      }
      case "deduction":
        if (!p) throw new Error("query required");
        result = await client.deduce(p);
        break;
      case "what_if": {
        const parts = split(p);
        const base = parts[0];
        const mod = parts[1] ?? s;
        if (!base || !mod) throw new Error("base and modifier required");
        result = await client.whatIf(base, mod);
        break;
      }
      case "slice": {
        const parts = split(p);
        const q = parts[0];
        const mod = parts[1] ?? s;
        if (!q || !mod) throw new Error("query and modifier required");
        result = await client.slice(q, mod);
        break;
      }
      case "paradox_create": {
        const sources = (p || s)
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean);
        if (!sources.length || !s || !t)
          throw new Error("sources, generation_mode, collapse_mode required");
        result = await client.paradoxCreate(sources, s, t);
        break;
      }
      case "paradox_read": {
        const id = p || s;
        if (!id) throw new Error("paradox UUID required");
        result = await client.paradoxGet(id);
        break;
      }
      case "recovery": {
        const key = p || s;
        if (!key) throw new Error("key_id required");
        result = await client.recoveryIdentity(key);
        break;
      }
      default:
        throw new Error(`Unknown mode: ${mode}`);
    }
    queryOutput.value += prettyJson(result);
  } catch (err) {
    queryOutput.value += `ERROR: ${err instanceof Error ? err.message : err}`;
  }
  queryOutput.value += "\n" + "─".repeat(60);
}

async function refreshTab(tab: TabId) {
  switch (tab) {
    case "control":
      await refreshControl();
      break;
    case "events":
      await refreshEvents();
      break;
    case "modules":
      await refreshModules();
      break;
    case "cluster":
      await refreshCluster();
      break;
    case "analytics":
      await refreshAnalytics();
      break;
    case "query":
      break;
  }
}

async function refreshAll() {
  await withLoading("Refreshing…", async () => {
    await refreshControl();
    if (activeTab.value !== "control") {
      await refreshTab(activeTab.value);
    }
  });
}

watch(activeTab, (tab) => {
  refreshTab(tab);
});

watch(eventFilter, () => {
  if (eventsCache.value.length) {
    renderEvents(eventsCache.value, eventSource.value);
  }
});

onMounted(() => {
  pushLog(`INDB WUI ${WUI_BUILD} started`);
  pushLog(`API → ${apiBase.value || window.location.origin}`);
  refreshAll();
  pollTimer = setInterval(() => {
    refreshControl();
    if (["events", "modules", "cluster", "analytics"].includes(activeTab.value)) {
      refreshTab(activeTab.value);
    }
  }, 5000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="border-b border-indb-grey-light/50 bg-indb-grey/60 backdrop-blur-md sticky top-0 z-20">
      <div class="mx-auto max-w-[1600px] px-4 py-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex items-center gap-4">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indb-red/20 border border-indb-red/40 font-mono text-indb-red font-bold">
            IN
          </div>
          <div>
            <h1 class="text-lg font-semibold tracking-tight">INDB Console</h1>
            <p class="text-xs text-indb-muted font-mono">
              WUI {{ WUI_BUILD }}
              <span v-if="lastRefresh"> · {{ lastRefresh.toLocaleTimeString() }}</span>
            </p>
          </div>
        </div>
        <div class="flex flex-col sm:flex-row gap-2 sm:items-center flex-1 lg:max-w-xl">
          <input
            v-model="apiBaseInput"
            class="input flex-1"
            placeholder="API URL (empty = same origin)"
            @keyup.enter="applyApiBase"
          />
          <button type="button" class="btn-primary shrink-0" @click="applyApiBase">Connect</button>
          <button type="button" class="btn-ghost shrink-0" @click="refreshAll">Refresh</button>
        </div>
        <div v-if="loading" class="flex items-center gap-2 text-xs text-indb-yellow">
          <span class="inline-block h-2 w-2 rounded-full bg-indb-yellow animate-pulse" />
          {{ loadingMsg || "Loading…" }}
        </div>
      </div>
      <div class="mx-auto max-w-[1600px] px-4 pb-3">
        <TabBar :active="activeTab" @change="activeTab = $event" />
      </div>
    </header>

    <main class="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 space-y-6">
      <!-- CONTROL -->
      <section v-show="activeTab === 'control'" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Events" :value="eventsCount" />
          <StatCard label="Fusion" :value="fusionRate" tone="warn" />
          <StatCard label="Server" :value="serverStatus" :tone="serverTone" />
        </div>
        <p v-if="sysLine" class="text-sm text-indb-muted font-mono">{{ sysLine }}</p>
        <JsonOutput :text="logLines.join('\n')" />
      </section>

      <!-- EVENTS -->
      <section v-show="activeTab === 'events'" class="space-y-4">
        <div class="panel p-4 flex flex-col md:flex-row gap-3">
          <SelectField v-model="eventSource" class="md:w-56" @change="refreshEvents">
            <option v-for="opt in sourceOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </SelectField>
          <input
            v-model="eventFilter"
            class="input flex-1"
            placeholder="Filter events…"
            @keyup.enter="searchEvents"
          />
          <button type="button" class="btn-primary" @click="refreshEvents">Reload</button>
          <button type="button" class="btn-ghost" @click="searchEvents">API Search</button>
        </div>
        <p class="text-sm text-indb-muted">{{ eventStatus }}</p>
        <DataTable
          :columns="['ID', 'Time', 'Location', 'Content']"
          :rows="eventRows"
          empty="No events"
        />
      </section>

      <!-- MODULES -->
      <section v-show="activeTab === 'modules'" class="space-y-6">
        <div class="panel p-4">
          <h2 class="text-sm font-semibold uppercase tracking-widest text-indb-muted mb-4">
            Source Connectors
          </h2>
          <DataTable
            :columns="['Module', 'Enabled', 'Status', 'API Key']"
            :rows="moduleRows"
          >
            <template #cell-2="{ cell }">
              <span :class="moduleStatusClass(String(cell))">{{ cell }}</span>
            </template>
          </DataTable>
        </div>
        <div class="panel p-4">
          <h2 class="text-sm font-semibold uppercase tracking-widest text-indb-muted mb-4">
            Active Protocols
          </h2>
          <DataTable :columns="['Protocol', 'Status', 'Port']" :rows="protocolRows" />
          <p class="mt-3 text-xs text-indb-muted">{{ modulesStatus }}</p>
        </div>
      </section>

      <!-- CLUSTER -->
      <section v-show="activeTab === 'cluster'" class="space-y-4">
        <p class="text-sm font-mono text-indb-white/80">{{ clusterSummary }}</p>
        <DataTable
          :columns="['Endpoint', 'Status', 'Port', 'Raft', 'Term']"
          :rows="clusterRows"
        >
          <template #cell-1="{ cell }">
            <span :class="cell === 'UP' ? 'badge-ok' : 'badge-err'">{{ cell }}</span>
          </template>
        </DataTable>
      </section>

      <!-- QUERY -->
      <section v-show="activeTab === 'query'" class="space-y-4">
        <div class="panel p-4 space-y-3">
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-3">
            <SelectField v-model="queryMode" class="lg:col-span-3">
              <option v-for="m in QUERY_MODES" :key="m.key" :value="m.key">
                {{ m.label }}
              </option>
            </SelectField>
            <input
              v-model="queryPrimary"
              class="input lg:col-span-4"
              placeholder="Primary input…"
              @keyup.enter="runQuery"
            />
            <input
              v-model="querySecondary"
              class="input lg:col-span-2"
              placeholder="Secondary…"
            />
            <input
              v-model="queryTertiary"
              class="input lg:col-span-2"
              placeholder="Tertiary…"
            />
            <button type="button" class="btn-primary lg:col-span-1" @click="runQuery">Run</button>
          </div>
          <p class="text-xs text-indb-muted font-mono">{{ queryHint }}</p>
        </div>
        <JsonOutput :text="queryOutput" />
      </section>

      <!-- ANALYTICS -->
      <section v-show="activeTab === 'analytics'" class="space-y-4">
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="Health" :value="analyticsStats.health" />
          <StatCard label="Locations" :value="analyticsStats.locations" />
          <StatCard label="Tokens" :value="analyticsStats.tokens" />
          <StatCard label="Fusion Rate" :value="analyticsStats.fusion" tone="warn" />
          <StatCard label="WS Clients" :value="analyticsStats.ws" />
        </div>
        <div v-if="insights.length" class="panel p-4">
          <h2 class="text-xs uppercase tracking-widest text-indb-muted mb-3">Insights</h2>
          <ul class="space-y-2 text-sm">
            <li v-for="(item, i) in insights" :key="i" class="flex gap-2">
              <span class="text-indb-red">•</span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
        <JsonOutput :text="analyticsDetail" />
      </section>
    </main>

    <footer class="border-t border-indb-grey-light/30 py-4 text-center text-xs text-indb-muted">
      INDB Web Console ·
      <a href="/docs" class="text-indb-red hover:underline">API Docs</a>
    </footer>
  </div>
</template>
