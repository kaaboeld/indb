export type TabId =
  | "control"
  | "events"
  | "modules"
  | "cluster"
  | "query"
  | "analytics";

export interface EventRow {
  id: string;
  timestamp: number;
  location: string;
  content: string;
  fused: boolean;
}

export interface ModuleRow {
  name: string;
  enabled: boolean;
  status: string;
  needsKey: boolean;
  hasKey: boolean;
}

export interface ClusterRow {
  endpoint: string;
  url: string;
  status: string;
  port: string;
  raft: string;
  term: string;
}

export interface QueryMode {
  label: string;
  key: string;
  hint: string;
}

export const QUERY_MODES: QueryMode[] = [
  {
    label: "Interpret (Exhale)",
    key: "interpret",
    hint: "mood | location [| goal]",
  },
  { label: "Prism Synthesize", key: "prism", hint: "event ID or query text" },
  {
    label: "Prism Instinct",
    key: "instinct",
    hint: "query [| adrenaline]",
  },
  { label: "Lens Query", key: "lens", hint: "context_a | context_b" },
  { label: "Echo Resonate", key: "echo", hint: "seed event UUID" },
  { label: "Deduction", key: "deduction", hint: "evidence query text" },
  { label: "What-If", key: "what_if", hint: "base_query | modifier" },
  { label: "Context Slice", key: "slice", hint: "query | modifier" },
  {
    label: "Paradox Create",
    key: "paradox_create",
    hint: "source IDs (comma-separated) + modes",
  },
  { label: "Paradox Read", key: "paradox_read", hint: "paradox UUID" },
  { label: "Recovery Identity", key: "recovery", hint: "key_id (SHA-256)" },
];
