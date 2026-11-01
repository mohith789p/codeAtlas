import React, { useEffect, useState } from 'react';
import { X, ExternalLink, FileCode } from 'lucide-react';
import { filesApi } from '../../files/api/files';
import type { Citation } from '../types';
import { dashboardCache } from '../../../services/api/cache';
import { Spinner } from '../../../shared/components/ui/States';
import './ChatSplitViewer.css';

interface ChatSplitViewerProps {
  repoId: string;
  citation: Citation;
  onClose: () => void;
  onOpenFull: (citation: Citation) => void;
}

export const ChatSplitViewer: React.FC<ChatSplitViewerProps> = ({
  repoId,
  citation,
  onClose,
  onOpenFull,
}) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const cached = dashboardCache.getFile(repoId, citation.file);
    if (cached) {
      setContent(cached.content);
      setLoading(false);
      return;
    }
    setLoading(true);
    filesApi.getFile(repoId, citation.file)
      .then((res) => {
        if (cancelled) return;
        dashboardCache.setFile(repoId, citation.file, res.content, res.language);
        setContent(res.content);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, citation.file]);

  const lines = content.split('\n');
  const start = citation.line_start ?? 1;
  const end = citation.line_end ?? start;

  return (
    <div className="chat-split-drawer">
      <div className="chat-split-header">
        <div className="chat-split-title">
          <FileCode size={14} color="var(--accent-violet-soft)" />
          <span>{citation.file}</span>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            (L{start}{end !== start ? `-${end}` : ''})
          </span>
        </div>
        <div className="chat-split-actions">
          <button
            type="button"
            className="btn-icon-subtle"
            onClick={() => onOpenFull(citation)}
            title="Open in Files explorer"
          >
            <ExternalLink size={14} />
          </button>
          <button type="button" className="btn-icon-subtle" onClick={onClose} title="Close preview">
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="chat-split-body">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}>
            <Spinner size={20} />
          </div>
        ) : (
          lines.map((line, idx) => {
            const lineNum = idx + 1;
            const highlighted = lineNum >= start && lineNum <= end;
            return (
              <div
                key={lineNum}
                className={`code-line ${highlighted ? 'code-line-highlighted' : ''}`}
              >
                <span className="code-line-number">{lineNum}</span>
                <span className="code-line-content">{line || ' '}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
