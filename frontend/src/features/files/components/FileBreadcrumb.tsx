import React, { useState } from 'react';
import { Copy, Check, FileCode } from 'lucide-react';

interface FileBreadcrumbProps {
  path: string;
  language: string;
  lineCount: number;
  content: string;
}

export const FileBreadcrumb: React.FC<FileBreadcrumbProps> = ({
  path,
  language,
  lineCount,
  content,
}) => {
  const [copied, setCopied] = useState(false);
  const segments = path.split('/').filter(Boolean);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="file-breadcrumb-bar">
      <div className="file-breadcrumb-path">
        <FileCode size={14} style={{ color: 'var(--accent-violet-soft)' }} />
        {segments.map((s, idx) => (
          <React.Fragment key={idx}>
            {idx > 0 && <span style={{ opacity: 0.4 }}>/</span>}
            <span style={{ color: idx === segments.length - 1 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
              {s}
            </span>
          </React.Fragment>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {lineCount} lines &bull; {language}
        </span>
        <button
          type="button"
          className="btn-icon-copy"
          onClick={handleCopy}
          title="Copy file contents"
        >
          {copied ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
};
