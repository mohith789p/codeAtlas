import React, { useState } from 'react';
import type { FileNode } from '../types';
import { FileTreeNode } from './FileTreeNode';
import { Spinner } from '../../../shared/components/ui/States';
import './FileTree.css';

interface FileTreeProps {
  nodes: FileNode[];
  selectedPath: string | null;
  onSelect: (node: FileNode) => void;
  loading: boolean;
  error?: string;
}

export const FileTree: React.FC<FileTreeProps> = ({
  nodes,
  selectedPath,
  onSelect,
  loading,
  error,
}) => {
  const [filter, setFilter] = useState('');

  return (
    <aside className="file-tree" aria-label="Repository files explorer">
      <div className="file-tree-header">
        <div className="file-tree-title-row">
          <span>Files Explorer</span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{nodes.length} roots</span>
        </div>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="file-search-input"
            placeholder="Filter files..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>

      <div className="file-tree-body">
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}>
            <Spinner size={20} />
          </div>
        )}
        {error && (
          <p style={{ padding: 'var(--space-3)', color: 'var(--error)', fontSize: 'var(--text-meta)' }}>
            {error}
          </p>
        )}
        {!loading && !error && nodes.map((n) => (
          <FileTreeNode
            key={n.path}
            node={n}
            selectedPath={selectedPath}
            onSelect={onSelect}
            filterText={filter}
          />
        ))}
      </div>
    </aside>
  );
};
