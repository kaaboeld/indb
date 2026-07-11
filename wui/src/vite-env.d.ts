/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_INDB_API_URL?: string;
  readonly VITE_INDB_CLUSTER_NODES?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
