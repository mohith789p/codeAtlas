import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { ExternalLink, GitBranch, Globe, User, FileText, FolderOpen, Users, Unlink, Star, GitFork, CircleDot, Check, Circle } from 'lucide-react';
import { repositoriesApi, type Repository } from '../../api/repositories';
import { chatApi } from '../../api/chat';
import { dashboardCache } from '../../api/cache';
import type { DashboardContextType } from '../../components/layout/DashboardShell';
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
  const outletContext = useOutletContext<DashboardContextType | null>();

  const initialRepo = outletContext?.repository || (repoId ? dashboardCache.getRepository(repoId) : null);
  const isReady = !!(initialRepo && (initialRepo.metadata_ready || initialRepo.status === 'ready'));
  const [fetchState, setFetchState] = useState<FetchState>(() => isReady ? 'success' : 'loading');
  const [repo, setRepo] = useState<Repository | null>(() => initialRepo);
  const [errorMsg, setErrorMsg] = useState('');
  const [unlinking, setUnlinking] = useState(false);
  const metadataReadyRef = useRef(isReady);

  const handleUnlink = async () => {
    if (!repoId || unlinking) return;
    setUnlinking(true);
    try {
      await chatApi.deleteSessions(repoId);
    } finally {
      dashboardCache.clear(repoId);
      navigate('/', { replace: true });
    }
  };

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    const controller = new AbortController();

    const currentRepo = outletContext?.repository || dashboardCache.getRepository(repoId);
    if (currentRepo) {
      setRepo(currentRepo);
      if (currentRepo.metadata_ready || currentRepo.status === 'ready') {
        metadataReadyRef.current = true;
        setFetchState('success');
      }
      if (currentRepo.status === 'ready') {
        return () => controller.abort();
      }
    } else {
      setFetchState('loading');
    }

    repositoriesApi
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: (data) => {
          if (cancelled) return;
          setRepo(data);
          dashboardCache.setRepository(repoId, data);
          if (data.metadata_ready || data.status === 'ready') {
            metadataReadyRef.current = true;
            setFetchState('success');
          }
        },
      })
      .then((readyData) => {
        if (cancelled) return;
        setRepo(readyData);
        dashboardCache.setRepository(repoId, readyData);
        metadataReadyRef.current = true;
        setFetchState('success');
      })
      .catch((err) => {
        if (!cancelled && err?.name !== 'AbortError') {
          console.error('[OverviewPage] Repository fetch error:', err);
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
  }, [repoId, outletContext?.repository]);

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
      {/* 1. Compact Repository Header */}
      <header className="overview-header" aria-label="Repository header">
        <div className="overview-header-main">
          <div className="overview-title-row">
            <h1 className="overview-repo-name">{repo.full_name ?? repo.name}</h1>
            {repo.status && (
              <span className={`overview-status-badge status-${repo.status}`} role="status">
                <span className="status-badge-dot" aria-hidden="true" />
                {statusLabel(repo.status)}
              </span>
            )}
          </div>
          {repo.description && (
            <p className="overview-description">{repo.description}</p>
          )}
          <div className="overview-header-meta">
            {repo.language && (
              <span className="overview-meta-item">
                {langColor && (
                  <span
                    className="lang-dot"
                    style={{ backgroundColor: langColor }}
                    aria-hidden="true"
                  />
                )}
                {repo.language}
              </span>
            )}
            {repo.branch && (
              <span className="overview-meta-item">
                <GitBranch size={13} aria-hidden="true" />
                {repo.branch}
              </span>
            )}
            {repo.url && (
              <a
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="overview-link"
                aria-label={`View ${repo.name} on source`}
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
        </div>

        <div className="overview-header-actions">
          <button
            className="overview-unlink-button"
            type="button"
            onClick={handleUnlink}
            disabled={unlinking}
            title="Unlink repository"
          >
            <Unlink size={13} aria-hidden="true" />
            {unlinking ? 'Unlinking…' : 'Unlink'}
          </button>
        </div>
      </header>

      {/* 2. Repository Scale Metrics — responsive grid utilizing horizontal space */}
      <section className="overview-section" aria-label="Repository statistics">
        <div className="overview-section-header">
          <p className="overview-section-label">Scale</p>
        </div>
        <div className="stats-grid" role="list">
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
          <StatCard
            number={formatNumber(repo.stats.stars)}
            label="Stars"
            icon={<Star size={14} aria-hidden="true" />}
          />
          <StatCard
            number={formatNumber(repo.stats.forks)}
            label="Forks"
            icon={<GitFork size={14} aria-hidden="true" />}
          />
          <StatCard
            number={formatNumber(repo.stats.open_issues)}
            label="Issues"
            icon={<CircleDot size={14} aria-hidden="true" />}
          />
          {repo.stats.open_pull_requests !== undefined && (
            <StatCard
              number={formatNumber(repo.stats.open_pull_requests)}
              label="Pull Requests"
            />
          )}
          {repo.stats.size_kb !== undefined && (
            <StatCard
              number={repo.stats.size_kb >= 1024
                ? `${(repo.stats.size_kb / 1024).toFixed(1)} MB`
                : `${repo.stats.size_kb} KB`}
              label="Disk Size"
            />
          )}
        </div>
      </section>

      {/* 3. CodeAtlas Processing / Status — placed directly below stats for immediate readiness visibility */}
      <section aria-label="CodeAtlas processing" className="processing-section">
        <div className="processing-header">
          <p className="overview-section-label">CodeAtlas Processing Status</p>
          {(formatDuration(repo.processing?.duration_ms) || formatDate(repo.processing?.last_indexed_at)) && (
            <span className="processing-meta">
              {formatDuration(repo.processing?.duration_ms) ? `Indexed in ${formatDuration(repo.processing?.duration_ms)}` : ''}
              {formatDate(repo.processing?.last_indexed_at) ? ` · Last indexed ${formatDate(repo.processing?.last_indexed_at)}` : ''}
            </span>
          )}
        </div>
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
                  {complete ? <Check size={14} /> : active ? <Spinner size={16} /> : <Circle size={10} />}
                </span>
                <div className="processing-step-info">
                  <span className="processing-label">{label}</span>
                  {stage === 'chunks' && repo.processing?.chunks_created !== undefined && (
                    <span className="processing-count">{formatNumber(repo.processing.chunks_created)} chunks</span>
                  )}
                  {stage === 'embeddings' && repo.processing?.embeddings_generated !== undefined && (
                    <span className="processing-count">{formatNumber(repo.processing.embeddings_generated)} vectors</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. Balanced Two-Column Section: Details & Technical Info (Left) | Languages, Topics & Contributors (Right) */}
      <div className="overview-main-grid">
        {/* Left Column: Repository Details */}
        <section className="overview-card" aria-label="Repository details">
          <p className="overview-section-label">Details</p>
          <dl className="metadata-list">
            {repo.owner && (
              <div className="metadata-row">
                <dt className="metadata-label">
                  <User size={13} aria-hidden="true" />
                  Owner
                </dt>
                <dd className="metadata-value">{repo.owner}</dd>
              </div>
            )}
            {repo.branch && (
              <div className="metadata-row">
                <dt className="metadata-label">
                  <GitBranch size={13} aria-hidden="true" />
                  Default Branch
                </dt>
                <dd className="metadata-value">{repo.branch}</dd>
              </div>
            )}
            {repo.language && (
              <div className="metadata-row">
                <dt className="metadata-label">Primary Language</dt>
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
              </div>
            )}
            {repo.url && (
              <div className="metadata-row">
                <dt className="metadata-label">Repository URL</dt>
                <dd className="metadata-value">
                  <a href={repo.url} target="_blank" rel="noopener noreferrer">
                    {repo.url}
                  </a>
                </dd>
              </div>
            )}
            {repositoryMetadata.visibility && (
              <div className="metadata-row">
                <dt className="metadata-label">Visibility</dt>
                <dd className="metadata-value capitalize">{repositoryMetadata.visibility}</dd>
              </div>
            )}
            {formatDate(repositoryMetadata.github_created_at) && (
              <div className="metadata-row">
                <dt className="metadata-label">Created</dt>
                <dd className="metadata-value">{formatDate(repositoryMetadata.github_created_at)}</dd>
              </div>
            )}
            {formatDate(repositoryMetadata.pushed_at || repositoryMetadata.github_updated_at) && (
              <div className="metadata-row">
                <dt className="metadata-label">Last Pushed</dt>
                <dd className="metadata-value">{formatDate(repositoryMetadata.pushed_at || repositoryMetadata.github_updated_at)}</dd>
              </div>
            )}
            {repositoryMetadata.license_name && (
              <div className="metadata-row">
                <dt className="metadata-label">License</dt>
                <dd className="metadata-value">{repositoryMetadata.license_name}</dd>
              </div>
            )}
          </dl>
        </section>

        {/* Right Column: Stack & Contributors */}
        <div className="overview-side-col">
          {/* Languages & Topics Card */}
          <section className="overview-card" aria-label="Languages and topics">
            <div className="side-card-section">
              <p className="overview-section-label">Languages</p>
              {languages.length > 0 ? (
                <div className="language-list">
                  {languages.map(([language, percentage]) => (
                    <div className="language-row" key={language}>
                      <span className="language-name">
                        <span
                          className="lang-dot"
                          style={{ backgroundColor: LANG_COLORS[language] ?? LANG_COLORS.Other }}
                          aria-hidden="true"
                        />
                        {language}
                      </span>
                      <span className="language-percentage">{percentage}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="overview-muted">Language breakdown unavailable.</p>
              )}
            </div>

            <div className="side-card-divider" />

            <div className="side-card-section">
              <p className="overview-section-label">Topics</p>
              {repositoryMetadata.topics && repositoryMetadata.topics.length > 0 ? (
                <div className="topic-list">
                  {repositoryMetadata.topics.map((topic) => (
                    <span className="topic-chip" key={topic}>{topic}</span>
                  ))}
                </div>
              ) : (
                <p className="overview-muted">No repository topics provided.</p>
              )}
            </div>
          </section>

          {/* Compact Contributors Card */}
          <section className="overview-card" aria-label="Contributors">
            <div className="contributors-card-header">
              <p className="overview-section-label">Contributors</p>
              {contributors.length > 0 && (
                <span className="contributors-count-badge">
                  {contributors.length} total
                </span>
              )}
            </div>
            {visibleContributors.length > 0 ? (
              <ul className="contributors-compact-list" role="list">
                {visibleContributors.map((c) => (
                  <li key={c.username} className="contributor-compact-item" role="listitem">
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
                    <div className="contributor-compact-info">
                      <span className="contributor-name">{c.username}</span>
                      {c.commits !== undefined && (
                        <span className="contributor-commits">
                          {c.commits} {c.commits === 1 ? 'commit' : 'commits'}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="overview-muted">Contributor data is unavailable for this repository.</p>
            )}
          </section>
        </div>
      </div>
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
