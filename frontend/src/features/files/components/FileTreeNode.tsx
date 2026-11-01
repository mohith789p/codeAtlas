import React, { useState } from 'react';
import { Folder, FolderOpen, File, ChevronRight } from 'lucide-react';
import type { FileNode } from '../types';

interface FileTreeNodeProps {
  node: FileNode;
  depth?: number;
  selectedPath: string | null;
  onSelect: (node: FileNode) => void;
  filterText?: string;
}

export const FileTreeNode: React.FC<FileTreeNodeProps> = ({
  node,
  depth = 0,
  selectedPath,
  onSelect,
  filterText = '',
}) => {
  const isDir = node.type === 'directory';
  const isSelected = node.path === selectedPath;
  const [open, setOpen] = useState(depth === 0 || filterText.length > 0);

  // If filtering, hide nodes that don't match or have no matching children
  if (filterText && !node.name.toLowerCase().includes(filterText.toLowerCase()) && !node.children?.some(c => c.name.toLowerCase().includes(filterText.toLowerCase()))) {
    return null;
  }

  const handleClick = () => {
    if (isDir) setOpen((v) => !v);
    else onSelect(node);
  };

  return (
    <div>
      <button
        className={['tree-item', isSelected ? 'tree-item-selected' : ''].filter(Boolean).join(' ')}
        style={{ paddingLeft: `${12 + depth * 12}px` }}
        onClick={handleClick}
        title={node.path}
        type="button"
      >
        <span className="tree-item-icon">
          {isDir ? (open ? <FolderOpen size={14} /> : <Folder size={14} />) : <File size={14} />}
        </span>
        {isDir && (
          <ChevronRight
            size={12}
            style={{
              transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 0.15s ease',
              color: 'var(--text-muted)',
              flexShrink: 0,
            }}
          />
        )}
        <span className="tree-item-name">{node.name}</span>
      </button>

      {isDir && open && node.children && (
        <div role="group">
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              filterText={filterText}
            />
          ))}
        </div>
      )}
    </div>
  );
};
