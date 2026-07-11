export function unwrap<T>(payload: unknown): T {
  if (payload && typeof payload === "object" && "data" in payload) {
    return (payload as { data: T }).data;
  }
  return payload as T;
}

export function formatTimestamp(ts: number): string {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function truncate(text: string, max = 80): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

export function eventContent(event: Record<string, unknown>): string {
  const anchor = event.raw_data_anchor ?? event.tokens;
  if (Array.isArray(anchor)) return anchor.join(" ");
  if (typeof anchor === "string") return anchor;
  return String(event.content ?? "—");
}

export function eventIdShort(event: Record<string, unknown>): string {
  const id = String(event.id ?? event.event_id ?? "—");
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}

export function locationLabel(loc: string, max = 40): string {
  if (!loc) return "—";
  return loc.length > max ? `…${loc.slice(-max + 1)}` : loc;
}

export function prettyJson(value: unknown, limit = 8000): string {
  try {
    const text = JSON.stringify(value, null, 2);
    return text.length > limit ? `${text.slice(0, limit)}\n…` : text;
  } catch {
    return String(value);
  }
}

export function moduleStatusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "running") return "text-emerald-400";
  if (s === "disabled") return "text-indb-muted";
  if (s === "error" || s === "no_api_key") return "text-indb-red";
  return "text-indb-yellow";
}

export function nodeStatusClass(ok: boolean): string {
  return ok ? "text-emerald-400" : "text-indb-red";
}
