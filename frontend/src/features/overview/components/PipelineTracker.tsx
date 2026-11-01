import React from 'react';
import { Check, Loader2 } from 'lucide-react';
import type { Repository } from '../../repositories/types';
import './PipelineTracker.css';

interface PipelineTrackerProps {
  repo: Repository;
}

function isStageComplete(repo: Repository, stageId: string): boolean {
  if (repo.status === 'ready') return true;
  if (stageId === 'metadata') return !!repo.metadata_ready || repo.status !== 'queued';
  if (stageId === 'files') return !!repo.files_ready || ['chunking', 'embedding', 'indexing'].includes(repo.status || '');
  if (stageId === 'chunks') return ['embedding', 'indexing'].includes(repo.status || '');
  if (stageId === 'embeddings') return repo.status === 'indexing';
  return false;
}

export const PipelineTracker: React.FC<PipelineTrackerProps> = ({ repo }) => {
  const isReady = repo.status === 'ready';

  const chunkCount =
    repo.processing?.chunks_created ??
    repo.processing_stats?.chunks_created ??
    repo.chunks;

  const embeddingCount =
    repo.processing?.embeddings_generated ??
    repo.processing_stats?.embeddings_generated ??
    repo.embeddings;

  const stages = [
    { id: 'metadata', label: '1. Metadata', desc: repo.branch ? `Branch: ${repo.branch}` : 'Repo info & branch' },
    { id: 'files', label: '2. Files', desc: repo.files ? `${repo.files.toLocaleString()} files mapped` : 'Tree structure' },
    {
      id: 'chunks',
      label: '3. Parsing',
      desc: chunkCount !== undefined && chunkCount !== null
        ? `AST code chunks (${chunkCount.toLocaleString()} chunks)`
        : 'AST code chunks',
    },
    {
      id: 'embeddings',
      label: '4. Embeddings',
      desc: embeddingCount !== undefined && embeddingCount !== null
        ? `Vector index (${embeddingCount.toLocaleString()} embeddings)`
        : 'Vector index',
    },
    { id: 'ready', label: '5. Ready', desc: 'Chat & search ready' },
  ];

  return (
    <div className="pipeline-card">
      <div className="pipeline-header">
        <h3 className="lang-card-title">Indexing & Ingestion Pipeline</h3>
        <span style={{ fontSize: '0.75rem', color: isReady ? 'var(--success)' : 'var(--warning)' }}>
          {isReady ? 'Fully synchronized' : 'Processing in background...'}
        </span>
      </div>

      <div className="pipeline-steps-grid">
        {stages.map((s, idx) => {
          const complete = isStageComplete(repo, s.id);
          const active = !complete && (idx === 0 || isStageComplete(repo, stages[idx - 1].id));

          return (
            <div
              key={s.id}
              className={`pipeline-step ${complete ? 'step-completed' : ''} ${active ? 'step-active' : ''}`}
            >
              <div className="step-indicator-row">
                <span className="step-badge">
                  {complete ? <Check size={12} strokeWidth={3} /> : active ? <Loader2 size={12} className="spin" /> : idx + 1}
                </span>
                <span style={{ fontSize: '0.6875rem', color: complete ? 'var(--success)' : active ? 'var(--accent-violet-soft)' : 'var(--text-muted)' }}>
                  {complete ? 'Done' : active ? 'In Progress' : 'Pending'}
                </span>
              </div>
              <span className="step-name">{s.label}</span>
              <span className="step-desc">{s.desc}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
