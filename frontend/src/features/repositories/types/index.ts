export interface Contributor {
  username: string;
  avatar_url?: string;
  commits?: number;
  contributions?: number;
}

export interface ProcessingStats {
  files_total?: number;
  chunks_created?: number;
  embeddings_generated?: number;
  duration_ms?: number;
  last_indexed_at?: string;
}

export interface RepositoryStats {
  files?: number;
  folders?: number;
  contributors?: number;
  size_kb?: number;
  stars?: number;
  forks?: number;
}

export interface RepositoryMetadata {
  visibility?: string;
  github_created_at?: string;
  github_updated_at?: string;
  pushed_at?: string;
  languages?: Record<string, number>;
  topics?: string[];
  license_name?: string;
  file_paths?: string[];
}

export interface Repository {
  id: string;
  name: string;
  full_name?: string;
  description?: string;
  owner?: string;
  default_branch?: string;
  branch?: string;
  primary_language?: string;
  language?: string;
  url?: string;
  homepage?: string;
  size_kb?: number;
  visibility?: string;
  topics?: string[];
  stars?: number;
  forks?: number;
  languages?: Record<string, number>;
  created_at?: string;
  updated_at?: string;
  pushed_at?: string;
  contributors?: Contributor[];
  files?: number;
  folders?: number;
  processing?: ProcessingStats;
  processing_stats?: ProcessingStats;
  chunks?: number;
  embeddings?: number;
  status?: 'queued' | 'downloading' | 'filtering' | 'chunking' | 'embedding' | 'indexing' | 'ready' | 'failed';
  error?: string;
  metadata_ready?: boolean;
  files_ready?: boolean;
  stats?: RepositoryStats;
  repository_metadata?: RepositoryMetadata;
}

export interface RepositoryPollingOptions {
  intervalMs?: number;
  maxAttempts?: number;
  signal?: AbortSignal;
  onStatus?: (repository: Repository) => void;
}

export type IngestPayload =
  | { mode: 'url'; url: string; branch?: string }
  | { mode: 'manual'; username: string; name: string; branch?: string };
