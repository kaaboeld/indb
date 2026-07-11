import { unwrap } from "../utils/format";

export class IndbApiClient {
  baseUrl: string;
  lastError: string | null = null;

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private async request<T>(
    path: string,
    init?: RequestInit,
    fallback?: T,
  ): Promise<T> {
    try {
      const res = await fetch(this.url(path), init);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const payload = await res.json();
      this.lastError = null;
      return unwrap<T>(payload);
    } catch (err) {
      this.lastError = err instanceof Error ? err.message : String(err);
      if (fallback !== undefined) return fallback;
      throw err;
    }
  }

  async health(): Promise<Record<string, unknown>> {
    try {
      const res = await fetch(this.url("/health"));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.lastError = null;
      return await res.json();
    } catch (err) {
      this.lastError = err instanceof Error ? err.message : String(err);
      return { status: "error", error: this.lastError };
    }
  }

  analyticsOverview() {
    return this.request<Record<string, unknown>>(
      "/api/v2/analytics/overview",
      undefined,
      {},
    );
  }

  analyticsInsights() {
    return this.request<string[]>("/api/v2/analytics/insights", undefined, []);
  }

  fusionStats() {
    return this.request<Record<string, unknown>>(
      "/api/v2/fusion/stats",
      undefined,
      {},
    );
  }

  events(limit = 50, params: Record<string, string | number> = {}) {
    const qs = new URLSearchParams({
      limit: String(limit),
      ...Object.fromEntries(
        Object.entries(params).map(([k, v]) => [k, String(v)]),
      ),
    });
    return this.request<Record<string, unknown>[]>(
      `/api/v2/events?${qs}`,
      undefined,
      [],
    );
  }

  async eventsMixed(perSource = 10, maxTotal = 50) {
    const overview = await this.analyticsOverview();
    const top = overview?.database as Record<string, unknown> | undefined;
    const locations = top?.top_locations as Record<string, number> | undefined;
    if (!locations || !Object.keys(locations).length) {
      return this.events(maxTotal);
    }
    const merged: Record<string, unknown>[] = [];
    for (const location of Object.keys(locations)) {
      const batch = await this.events(perSource, {
        filter_key: "location",
        filter_value: location,
      });
      merged.push(...batch);
    }
    merged.sort(
      (a, b) => Number(b.timestamp ?? 0) - Number(a.timestamp ?? 0),
    );
    return merged.slice(0, maxTotal);
  }

  search(q: string, limit = 50) {
    const qs = new URLSearchParams({ q, limit: String(limit) });
    return this.request<Record<string, unknown>[]>(
      `/api/v2/search?${qs}`,
      undefined,
      [],
    );
  }

  modules() {
    return this.request<Record<string, unknown>[]>(
      "/api/v2/modules",
      undefined,
      [],
    );
  }

  protocols() {
    return this.request<Record<string, unknown>>(
      "/api/v2/system/protocols",
      undefined,
      {},
    );
  }

  websocketStats() {
    return this.request<Record<string, unknown>>(
      "/api/v2/websocket/stats",
      undefined,
      {},
    );
  }

  async raftStatus(): Promise<Record<string, unknown>> {
    try {
      const res = await fetch(this.url("/raft/status"));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.lastError = null;
      return await res.json();
    } catch (err) {
      this.lastError = err instanceof Error ? err.message : String(err);
      return {};
    }
  }

  async nodeStatus(nodeUrl: string) {
    const base = nodeUrl.replace(/\/$/, "");
    try {
      const healthRes = await fetch(`${base}/health`);
      const healthOk = healthRes.ok;
      const healthData = healthOk ? await healthRes.json() : {};
      let raftData: Record<string, unknown> = {};
      try {
        const raftRes = await fetch(`${base}/raft/status`);
        if (raftRes.ok) raftData = await raftRes.json();
      } catch {
        /* optional */
      }
      return { ok: healthOk, data: { ...healthData, raft: raftData }, error: null };
    } catch (err) {
      return {
        ok: false,
        data: {},
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  interpret(mood: string, location: string, goal = "", limit = 10) {
    const body: Record<string, unknown> = {
      context: { mood, location },
      limit,
    };
    if (goal) (body.context as Record<string, string>).goal = goal;
    return this.request(
      "/api/v2/interpret",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
      { error: this.lastError },
    );
  }

  prismSynthesize(query: string, limit = 10) {
    return this.request(
      "/api/v2/prism/synthesize",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit }),
      },
      { error: this.lastError },
    );
  }

  prismInstinct(query: string, adrenaline: number) {
    return this.request(
      "/api/v2/prism/instinct",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, adrenaline, limit: 10 }),
      },
      { error: this.lastError },
    );
  }

  lensQuery(contextA: string, contextB: string, limit = 20) {
    return this.request(
      "/api/v2/lens/query",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context_a: contextA,
          context_b: contextB,
          ratio: [0.5, 0.5],
          limit,
        }),
      },
      { error: this.lastError },
    );
  }

  echoResonate(seedId: string) {
    return this.request(
      "/api/v2/echo/resonate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed_id: seedId, radius: 0.3, limit: 20 }),
      },
      { error: this.lastError },
    );
  }

  deduce(query: string) {
    return this.request(
      "/api/v2/deduction/deduce",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 15 }),
      },
      { error: this.lastError },
    );
  }

  whatIf(base: string, modifier: string) {
    return this.request(
      "/api/v2/what-if",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_query_type: "search",
          base_params: { q: base },
          what_if: modifier,
          mode: "core",
        }),
      },
      { error: this.lastError },
    );
  }

  slice(query: string, whatIf: string) {
    return this.request(
      "/api/v2/slice",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, what_if: whatIf, limit: 20 }),
      },
      { error: this.lastError },
    );
  }

  paradoxCreate(sources: string[], generationMode: string, collapseMode: string) {
    return this.request(
      "/api/v2/paradox",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sources,
          generation_mode: generationMode,
          collapse_mode: collapseMode,
        }),
      },
      { error: this.lastError },
    );
  }

  paradoxGet(id: string) {
    return this.request(
      `/api/v2/paradox/${id}?collapse=true`,
      undefined,
      { error: this.lastError },
    );
  }

  recoveryIdentity(keyId: string) {
    return this.request(
      `/api/v2/recovery/identity/${keyId}`,
      undefined,
      { error: this.lastError },
    );
  }
}

export function defaultApiBase(): string {
  const env = import.meta.env.VITE_INDB_API_URL as string | undefined;
  if (env) return env.replace(/\/$/, "");
  return "";
}

export function clusterNodes(apiUrl: string): { name: string; url: string; port: string }[] {
  const custom = import.meta.env.VITE_INDB_CLUSTER_NODES as string | undefined;
  if (custom) {
    return custom.split(",").map((u, i) => {
      const url = u.trim().replace(/\/$/, "");
      let port = "80";
      try {
        port = new URL(url).port || (url.startsWith("https") ? "443" : "80");
      } catch {
        /* ignore */
      }
      return { name: `node-${i + 1}`, url, port };
    });
  }
  const url = apiUrl.replace(/\/$/, "");
  let port = "80";
  let host = "api";
  try {
    const parsed = new URL(url);
    host = parsed.hostname || "api";
    port = parsed.port || (parsed.protocol === "https:" ? "443" : "80");
  } catch {
    /* ignore */
  }
  return [{ name: host, url, port }];
}
