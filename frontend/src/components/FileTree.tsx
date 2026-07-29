import React, { useState } from 'react';
import { FileNode } from '../types';
import { Folder, FolderOpen, FileCode, ChevronRight, ChevronDown } from 'lucide-react';

interface FileTreeProps {
  node: FileNode;
  onSelectFile: (fileId: number) => void;
  selectedFileId?: number;
}

export const FileTreeItem: React.FC<FileTreeProps> = ({ node, onSelectFile, selectedFileId }) => {
  const [isOpen, setIsOpen] = useState(true);

  if (node.type === 'file') {
    const isSelected = selectedFileId === node.id;
    return (
      <div
        onClick={() => node.id && onSelectFile(node.id)}
        className={`flex items-center space-x-2 px-2 py-1.5 rounded-lg text-xs font-mono cursor-pointer transition ${
          isSelected
            ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/30'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
        }`}
      >
        <FileCode className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-1.5 px-2 py-1.5 rounded-lg text-xs text-slate-300 font-medium cursor-pointer hover:bg-slate-800/40 transition"
      >
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
        )}
        {isOpen ? (
          <FolderOpen className="w-4 h-4 text-amber-400/80" />
        ) : (
          <Folder className="w-4 h-4 text-amber-400/80" />
        )}
        <span className="truncate">{node.name}</span>
      </div>

      {isOpen && node.children && (
        <div className="pl-4 border-l border-slate-800/80 ml-2 space-y-0.5">
          {node.children.map((child, idx) => (
            <FileTreeItem
              key={idx}
              node={child}
              onSelectFile={onSelectFile}
              selectedFileId={selectedFileId}
            />
          ))}
        </div>
      )}
    </div>
  );
};
