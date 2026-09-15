import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ExternalLink, GitBranch, Globe, User, FileText, FolderOpen, Users, LogOut, Star, GitFork, CircleDot, Check, Circle } from 'lucide-react';
import { repositoriesApi, type Repository } from '../../api/repositories';
import { chatApi } from '../../api/chat';
import { ApiError } from '../../api/client';
import { Spinner, EmptyState, ErrorState } from '../../components/ui/States';
import './OverviewPage.css';

// Language colour map — uses support tokens only, no new palette colours
const LANG_COLORS: Record<string, string> = {
  TypeScript: '#6366f1',
  JavaScript: '#fbbf24',
  Python: '#34d399',
  Rust: '#f87171',
  Go: '#94a3b8',
  Java: '#f87171',
  'C++': '#8b5cf6',
  C: '#8b5cf6',
  Ruby: '#f87171',
  Other: '#9a95a3',
};

function initials(name: string): string {
  return name
    .split(/[\s._-]/)
    .map((p) => p[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatNumber(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function formatDate(value?: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

function formatDuration(durationMs?: number): string | null {
  if (durationMs === undefined) return null;
  if (durationMs < 1000) return `${Math.round(durationMs)} ms`;
  return `${(durationMs / 1000).toFixed(1)} s`;
}

function stageComplete(repo: Repository, stage: string): boolean {
  if (stage === 'metadata') return repo.metadata_ready === true || repo.status === 'ready';
  if (stage === 'files') return repo.files_ready === true || repo.status === 'ready';
  if (stage === 'chunks') return ['embedding', 'indexing', 'ready'].includes(repo.status ?? '');
  if (stage === 'embeddings') return repo.status === 'indexing' || repo.status === 'ready';
  return repo.status === 'ready';
}

function statusLabel(status: Repository['status']): string {
  if (!status) return 'Status unavailable';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

type FetchState = 'loading' | 'success' | 'error';

export const OverviewPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const [fetchState, setFetchState] = useState<FetchState>('loading');
  const [repo, setRepo] = useState<Repository | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [exiting, setExiting] = useState(false);
  const metadataReadyRef = useRef(false);

  const handleExit = async () => {
    if (!repoId || exiting) return;
    setExiting(true);
    try {
      await chatApi.deleteSessions(repoId);
    } finally {
      navigate('/', { replace: true });
    }
  };

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    const controller = new AbortController();

    setFetchState('loading');
    repositoriesApi
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: (data) => {
          if (cancelled) return;
          setRepo(data);
          if (data.metadata_ready || data.status === 'ready') {
            metadataReadyRef.current = true;
            setFetchState('success');
          }
        },
      })
      .catch((err) => {
        if (!cancelled && err?.name !== 'AbortError') {
          if (metadataReadyRef.current) {
            setErrorMsg(err instanceof Error ? err.message : 'Repository ingestion failed.');
            return;
          }
          setErrorMsg(
            err instanceof ApiError || err instanceof Error
              ? err.message
              : 'Failed to load repository.',
          );
          setFetchState('error');
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [repoId]);

  if (fetchState === 'loading') {
    return (
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <Spinner size={28} />
      </div>
    );
  }

  if (fetchState === 'error') {
    return (
      <ErrorState
        title="Could not load repository"
        message={errorMsg}
        style={{ flex: 1 }}
      />
    );
  }

  if (!repo) {
    return <EmptyState title="No repository data" />;
  }

  const langColor = repo.language ? (LANG_COLORS[repo.language] ?? LANG_COLORS['Other']) : null;
  const contributors = repo.contributors ?? [];
  const visibleContributors = contributors.slice(0, 8);
  const repositoryMetadata = repo.repository_metadata ?? {};
  const languages = Object.entries(repositoryMetadata.languages ?? {}).sort(([, a], [, b]) => b - a);

  return (
    <div className="overview">
      <div className="overview-toolbar">
        <button className="overview-exit-button" type="button" onClick={handleExit} disabled={exiting}>
          <LogOut size={14} aria-hidden="true" />
          {exiting ? 'Exiting…' : 'Exit'}
        </button>
      </div>
      {/* 1. Repository Identity — strongest visual element */}
      <section className="overview-identity" aria-label="Repository identity">
        <h1 className="overview-repo-name">{repo.full_name ?? repo.name}</h1>
        {repo.description && (
          <p className="overview-description">{repo.description}</p>
        )}
        {repo.status && (
          <p className={`overview-ingestion-status status-${repo.status}`} role="status">
            Ingestion: {statusLabel(repo.status)}
            {repo.error ? ` — ${repo.error}` : ''}
          </p>
        )}
        <div className="overview-links">
          {repo.url && (
            <a
              href={repo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="overview-link"
              aria-label={`View ${repo.name} on its source`}
            >
              <ExternalLink size={13} aria-hidden="true" />
              Source
            </a>
          )}
          {repo.homepage && (
            <a
              href={repo.homepage}
              target="_blank"
              rel="noopener noreferrer"
              className="overview-link"
              aria-label={`Visit ${repo.name} homepage`}
            >
              <Globe size={13} aria-hidden="true" />
              Homepage
            </a>
          )}
        </div>
      </section>

      {/* 2. Statistics — compact horizontal row */}
      <section aria-label="Repository statistics">
        <p className="overview-section-label">Scale</p>
        <div className="stats-row" role="list">
          <StatCard
            number={formatNumber(repo.stats.files)}
            label="Files"
            icon={<FileText size={14} aria-hidden="true" />}
          />
          <StatCard
            number={formatNumber(repo.stats.folders)}
            label="Folders"
            icon={<FolderOpen size={14} aria-hidden="true" />}
          />
          <StatCard
            number={formatNumber(repo.stats.contributors)}
            label="Contributors"
            icon={<Users size={14} aria-hidden="true" />}
          />
          <StatCard number={formatNumber(repo.stats.stars)} label="Stars" icon={<Star size={14} aria-hidden="true" />} />
          <StatCard number={formatNumber(repo.stats.forks)} label="Forks" icon={<GitFork size={14} aria-hidden="true" />} />
          <StatCard number={formatNumber(repo.stats.open_issues)} label="Open issues" icon={<CircleDot size={14} aria-hidden="true" />} />
          {repo.stats.open_pull_requests !== undefined && (
            <StatCard number={formatNumber(repo.stats.open_pull_requests)} label="Open PRs" />
          )}
          {repo.stats.size_kb !== undefined && (
            <StatCard
              number={repo.stats.size_kb >= 1024
                ? `${(repo.stats.size_kb / 1024).toFixed(1)} MB`
                : `${repo.stats.size_kb} KB`}
              label="Size"
            />
          )}
        </div>
      </section>

      {/* 3. Metadata — label/value pairs, no card wrapper */}
      <section aria-label="Repository metadata">
        <p className="overview-section-label">Details</p>
        <dl className="metadata-list">
          {repo.owner && (
            <>
              <dt className="metadata-label">
                <User size={12} aria-hidden="true" style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Owner
              </dt>
              <dd className="metadata-value">{repo.owner}</dd>
            </>
          )}
          {repo.branch && (
            <>
              <dt className="metadata-label">
                <GitBranch size={12} aria-hidden="true" style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Branch
              </dt>
              <dd className="metadata-value">{repo.branch}</dd>
            </>
          )}
          {repo.language && (
            <>
              <dt className="metadata-label">Language</dt>
              <dd className="metadata-value" style={{ display: 'flex', alignItems: 'center' }}>
                {langColor && (
                  <span
                    className="lang-dot"
                    style={{ backgroundColor: langColor }}
                    aria-hidden="true"
                  />
                )}
                {repo.language}
              </dd>
            </>
          )}
          {repo.url && (
            <>
              <dt className="metadata-label">URL</dt>
              <dd className="metadata-value">
                <a href={repo.url} target="_blank" rel="noopener noreferrer">
                  {repo.url}
                </a>
              </dd>
            </>
          )}
          {repositoryMetadata.visibility && (
            <>
              <dt className="metadata-label">Visibility</dt>
              <dd className="metadata-value">{repositoryMetadata.visibility}</dd>
            </>
          )}
          {formatDate(repositoryMetadata.github_created_at) && (
            <>
              <dt className="metadata-label">Created</dt>
              <dd className="metadata-value">{formatDate(repositoryMetadata.github_created_at)}</dd>
            </>
          )}
          {formatDate(repositoryMetadata.pushed_at || repositoryMetadata.github_updated_at) && (
            <>
              <dt className="metadata-label">Last pushed</dt>
              <dd className="metadata-value">{formatDate(repositoryMetadata.pushed_at || repositoryMetadata.github_updated_at)}</dd>
            </>
          )}
          {repositoryMetadata.license_name && (
            <>
              <dt className="metadata-label">License</dt>
              <dd className="metadata-value">{repositoryMetadata.license_name}</dd>
            </>
          )}
        </dl>
      </section>

      <div className="overview-info-grid">
        <section aria-label="Languages">
          <p className="overview-section-label">Languages</p>
          {languages.length > 0 ? (
            <div className="language-list">
              {languages.map(([language, percentage]) => (
                <div className="language-row" key={language}>
                  <span className="language-name"><span className="lang-dot" style={{ backgroundColor: LANG_COLORS[language] ?? LANG_COLORS.Other }} aria-hidden="true" />{language}</span>
                  <span className="language-percentage">{percentage}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="overview-muted">Language breakdown unavailable.</p>
          )}
        </section>

        <section aria-label="Topics">
          <p className="overview-section-label">Topics</p>
          {repositoryMetadata.topics && repositoryMetadata.topics.length > 0 ? (
            <div className="topic-empty">
              {repositoryMetadata.topics.map((topic) => <span className="topic-chip" key={topic}>{topic}</span>)}
            </div>
          ) : (
            <p className="overview-muted">No repository topics provided.</p>
          )}
        </section>
      </div>

      {/* 4. Contributors — lowest visual priority */}
      <section aria-label="Contributors">
        <p className="overview-section-label">Contributors</p>
        {visibleContributors.length > 0 ? (
          <ul className="contributors-list" role="list">
            {visibleContributors.map((c) => (
              <li key={c.username} className="contributor-row" role="listitem">
                <div className="contributor-avatar">
                  {c.avatar_url ? (
                    <img
                      src={c.avatar_url}
                      alt={`${c.username}'s avatar`}
                    />
                  ) : (
                    <span aria-hidden="true">{initials(c.username)}</span>
                  )}
                </div>
                <div className="contributor-info">
                  <p className="contributor-name">{c.username}</p>
                  {c.commits !== undefined && (
                    <p className="contributor-commits">
                      {c.commits} {c.commits === 1 ? 'commit' : 'commits'}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="contributors-empty">Contributor data is unavailable for this repository.</p>
        )}
        {contributors.length > visibleContributors.length && (
          <p className="contributors-more">
            Showing the top {visibleContributors.length} of {contributors.length} contributors.
          </p>
        )}
      </section>

      <section aria-label="CodeAtlas processing" className="processing-section">
        <p className="overview-section-label">CodeAtlas Processing</p>
        <div className="processing-grid">
          {[
            ['metadata', 'Metadata extracted'],
            ['files', 'Files processed'],
            ['chunks', 'Chunks created'],
            ['embeddings', 'Embeddings generated'],
            ['search', 'Search index ready'],
          ].map(([stage, label]) => {
            const complete = stageComplete(repo, stage);
            const active = !complete && repo.status !== 'failed' && (
              (stage === 'metadata' && repo.status === 'downloading') ||
              (stage === 'files' && repo.status === 'filtering') ||
              (stage === 'chunks' && repo.status === 'chunking') ||
              (stage === 'embeddings' && repo.status === 'embedding') ||
              (stage === 'search' && repo.status === 'indexing')
            );
            return (
              <div
                className={`processing-step ${complete ? 'processing-step-complete' : active ? 'processing-step-active' : 'processing-step-pending'}`}
                key={stage}
                aria-label={`${label}${complete ? ', complete' : active ? ', in progress' : ', pending'}`}
              >
                <span className={`processing-icon ${complete ? 'processing-complete' : ''}`} aria-hidden="true">
                  {complete ? <Check size={14} /> : active ? <Spinner size={20} /> : <Circle size={12} />}
                </span>
                <span className="processing-label">{label}</span>
                {stage === 'chunks' && repo.processing?.chunks_created !== undefined && <span className="processing-count">· {formatNumber(repo.processing.chunks_created)}</span>}
                {stage === 'embeddings' && repo.processing?.embeddings_generated !== undefined && <span className="processing-count">· {formatNumber(repo.processing.embeddings_generated)}</span>}
              </div>
            );
          })}
        </div>
        {(formatDuration(repo.processing?.duration_ms) || formatDate(repo.processing?.last_indexed_at)) && (
          <p className="processing-meta">
            {formatDuration(repo.processing?.duration_ms) ? `Indexed in ${formatDuration(repo.processing?.duration_ms)}` : ''}
            {formatDate(repo.processing?.last_indexed_at) ? ` · Last indexed ${formatDate(repo.processing?.last_indexed_at)}` : ''}
          </p>
        )}
      </section>
    </div>
  );
};

interface StatCardProps {
  number: string;
  label: string;
  icon?: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ number, label, icon }) => (
  <div className="stat-card" role="listitem">
    <span className="stat-number" aria-label={`${number} ${label}`}>
      {number}
    </span>
    <span className="stat-label">
      {icon && <span aria-hidden="true" style={{ marginRight: 4, verticalAlign: 'middle' }}>{icon}</span>}
      {label}
    </span>
  </div>
);
