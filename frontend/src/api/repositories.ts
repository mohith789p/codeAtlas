/**
 * Repository API
 *
 * Required endpoints (backend dependency):
 *
 * POST /api/repositories
 *   body: { mode: 'url', url: string, branch?: string }
 *      or { mode: 'manual', username: string, name: string, branch?: string }
 *   response: Repository
 *
 * GET /api/repositories/:id
 *   response: Repository
 */

import { get, post } from './client';

const wait = (milliseconds: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('The operation was aborted.', 'AbortError'));
      return;
    }

    const onAbort = () => {
      window.clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
      reject(new DOMException('The operation was aborted.', 'AbortError'));
    };
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, milliseconds);
    signal?.addEventListener('abort', onAbort, { once: true });
  });

export class RepositoryIngestionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RepositoryIngestionError';
  }
}

export interface RepositoryStats {
  files: number;
  folders: number;
  contributors: number;
  size_kb?: number;
  stars: number;
  forks: number;
  open_issues: number;
  open_pull_requests?: number;
}

export interface Contributor {
  username: string;
  avatar_url?: string;
  commits?: number;
}

export interface RepositoryMetadata {
  visibility?: string;
  github_created_at?: string;
  github_updated_at?: string;
  pushed_at?: string;
  languages?: Record<string, number>;
  topics?: string[];
  license_name?: string;
}

export interface ProcessingStats {
  chunks_created?: number;
  embeddings_generated?: number;
  duration_ms?: number;
  last_indexed_at?: string;
}

export interface Repository {
  id: string;
  name: string;
  full_name?: string;
  description?: string;
  owner?: string;
  branch?: string;
  language?: string;
  url?: string;
  homepage?: string;
  stats: RepositoryStats;
  contributors?: Contributor[];
  repository_metadata?: RepositoryMetadata;
  processing?: ProcessingStats;
  created_at?: string;
  updated_at?: string;
  status?: 'queued' | 'downloading' | 'filtering' | 'chunking' | 'embedding' | 'indexing' | 'ready' | 'failed';
  error?: string;
  metadata_ready?: boolean;
  files_ready?: boolean;
}

export interface RepositoryPollingOptions {
  intervalMs?: number;
  maxAttempts?: number;
  signal?: AbortSignal;
  onStatus?: (repository: Repository) => void;
}

export type IngestPayload =
  | { mode: 'url';    url: string;                            branch?: string }
  | { mode: 'manual'; username: string; name: string;        branch?: string };


export const repositoriesApi = {
  ingest: (payload: IngestPayload) =>
    post<Repository>('/repositories', payload),

  get: (id: string, opts?: RequestInit) =>
    get<Repository>(`/repositories/${id}`, opts),

  list: () =>
    get<Repository[]>('/repositories'),

  waitUntilReady: async (
    id: string,
    options: RepositoryPollingOptions = {},
  ): Promise<Repository> => {
    return waitForReadiness(id, (repository) => repository.status === 'ready', options);
  },

  waitUntilMetadataReady: async (
    id: string,
    options: RepositoryPollingOptions = {},
  ): Promise<Repository> => {
    return waitForReadiness(id, (repository) => repository.metadata_ready === true || repository.status === 'ready', options);
  },

  waitUntilFilesReady: async (
    id: string,
    options: RepositoryPollingOptions = {},
  ): Promise<Repository> => {
    return waitForReadiness(id, (repository) => repository.files_ready === true || repository.status === 'ready', options);
  },

  monitorUntilReady: async (
    id: string,
    options: RepositoryPollingOptions = {},
  ): Promise<Repository> => waitForReadiness(id, () => false, options, true),
};

async function waitForReadiness(
  id: string,
  isReady: (repository: Repository) => boolean,
  options: RepositoryPollingOptions = {},
  monitorToTerminal = false,
): Promise<Repository> {
  const intervalMs = options.intervalMs ?? 1000;
  const maxAttempts = options.maxAttempts ?? 120;
  const { signal } = options;
  let repository = await repositoriesApi.get(id, { signal });
  options.onStatus?.(repository);

  for (let attempt = 0; attempt < maxAttempts && (monitorToTerminal
    ? repository.status !== 'ready' && repository.status !== 'failed'
    : !isReady(repository) && repository.status !== 'failed'); attempt += 1) {
    await wait(intervalMs, signal);
    repository = await repositoriesApi.get(id, { signal });
    options.onStatus?.(repository);
  }

  if (repository.status === 'failed' && !isReady(repository)) {
    throw new RepositoryIngestionError(
      repository.error || 'Repository ingestion failed.',
    );
  }

  if (monitorToTerminal && repository.status === 'ready') {
    return repository;
  }

  if (!isReady(repository)) {
    throw new RepositoryIngestionError(
      'Repository ingestion did not finish before the wait timeout.',
    );
  }

  return repository;
}
