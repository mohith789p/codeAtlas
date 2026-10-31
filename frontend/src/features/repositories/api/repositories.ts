import { get, post } from '../../../services/api/client';
import type { Repository, RepositoryPollingOptions, IngestPayload } from '../types';

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

export const repositoriesApi = {
  ingest: (payload: IngestPayload) => {
    const repositoryUrl =
      payload.mode === 'url'
        ? payload.url.trim()
        : `https://github.com/${payload.username.trim()}/${payload.name.trim()}`;
    return post<Repository>('/repositories', {
      repository_url: repositoryUrl,
      branch: payload.branch?.trim() || null,
    });
  },

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
