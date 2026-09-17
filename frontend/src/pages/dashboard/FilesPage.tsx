import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useSearchParams, useOutletContext } from 'react-router-dom';
import { Folder, FolderOpen, File, ChevronRight } from 'lucide-react';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import { filesApi, type FileNode } from '../../api/files';
import { repositoriesApi, type Repository } from '../../api/repositories';
import { dashboardCache } from '../../api/cache';
import type { DashboardContextType } from '../../components/layout/DashboardShell';
import { ApiError } from '../../api/client';
import { Spinner, EmptyState, ErrorState } from '../../components/ui/States';
import './FilesPage.css';

// ─── File Tree ──────────────────────────────────────────────────────────────

interface TreeNodeProps {
  node: FileNode;
  depth?: number;
  selectedPath: string | null;
  onSelect: (node: FileNode) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  depth = 0,
  selectedPath,
  onSelect,
}) => {
  const [open, setOpen] = useState(depth === 0);
  const isDir = node.type === 'directory';
  const isSelected = node.path === selectedPath;

  const handleClick = () => {
    if (isDir) setOpen((v) => !v);
    else onSelect(node);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
    if (e.key === 'ArrowRight' && isDir && !open) setOpen(true);
    if (e.key === 'ArrowLeft' && isDir && open) setOpen(false);
  };

  return (
    <div>
      <button
        className={[
          'tree-item',
          isSelected ? 'tree-item-selected' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        style={{ paddingLeft: `${var_space(3) + depth * 12}px` }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-expanded={isDir ? open : undefined}
        aria-selected={!isDir ? isSelected : undefined}
        role={isDir ? 'button' : 'option'}
        title={node.path}
      >
        <span className="tree-item-icon" aria-hidden="true">
          {isDir ? (
            open ? (
              <FolderOpen size={14} />
            ) : (
              <Folder size={14} />
            )
          ) : (
            <File size={14} />
          )}
        </span>
        {isDir && (
          <ChevronRight
            size={12}
            aria-hidden="true"
            style={{
              transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: `transform var(--duration-fast) var(--ease-out)`,
              color: 'var(--text-muted)',
              flexShrink: 0,
            }}
          />
        )}
        <span className="tree-item-name">{node.name}</span>
      </button>

      {isDir && open && node.children && (
        <div role="group" aria-label={node.name}>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Utility: compute pixel from CSS variable (approximate)
function var_space(n: number) {
  return n * 4; // rough: --space-3 = 12, etc
}

// ─── Breadcrumb ─────────────────────────────────────────────────────────────

interface BreadcrumbProps {
  path: string;
  onNavigate: (path: string) => void;
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({ path, onNavigate }) => {
  const parts = path.split('/').filter(Boolean);

  return (
    <nav className="breadcrumb" aria-label="File path">
      {parts.map((part, i) => {
        const isLast = i === parts.length - 1;
        const partPath = parts.slice(0, i + 1).join('/');

        if (isLast) {
          return (
            <React.Fragment key={partPath}>
              {i > 0 && <span className="breadcrumb-separator" aria-hidden="true">/</span>}
              <span className="breadcrumb-current" aria-current="page">
                {part}
              </span>
            </React.Fragment>
          );
        }

        return (
          <React.Fragment key={partPath}>
            {i > 0 && <span className="breadcrumb-separator" aria-hidden="true">/</span>}
            <button
              className="breadcrumb-segment clickable"
              onClick={() => onNavigate(partPath)}
              title={partPath}
            >
              {part}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
};

// ─── Code Viewer ─────────────────────────────────────────────────────────────

interface CodeViewerProps {
  content: string;
  language: string;
  highlightLines?: [number, number]; // [start, end] 1-indexed
}

const CodeViewer: React.FC<CodeViewerProps> = ({
  content,
  language,
  highlightLines,
}) => {


  // Apply syntax highlighting per line for correctness
  // We highlight the full source and extract line-level spans
  const highlighted = React.useMemo(() => {
    try {
      const lang = hljs.getLanguage(language) ? language : 'plaintext';
      return hljs.highlight(content, { language: lang }).value;
    } catch {
      return content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }
  }, [content, language]);

  // Split highlighted HTML by newlines (safe enough for line display)
  const highlightedLines = highlighted.split('\n');

  return (
    <div className="code-viewer" role="region" aria-label="File content">
      <div className="code-viewer-inner" aria-hidden="false">
        {highlightedLines.map((lineHtml, idx) => {
          const lineNum = idx + 1;
          const isHighlighted =
            highlightLines &&
            lineNum >= highlightLines[0] &&
            lineNum <= highlightLines[1];

          return (
            <div
              key={lineNum}
              className={[
                'code-line',
                isHighlighted ? 'code-line-highlighted' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              id={`L${lineNum}`}
            >
              <span className="code-line-number" aria-hidden="true">
                {lineNum}
              </span>
              <span
                className="code-line-content"
                // Using dangerouslySetInnerHTML is necessary here — hljs
                // returns HTML with <span> tags for syntax coloring.
                // The input is the file content from our own API, not user-generated HTML.
                dangerouslySetInnerHTML={{ __html: lineHtml || ' ' }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ─── Files Page ──────────────────────────────────────────────────────────────

type FetchState = 'idle' | 'loading' | 'success' | 'error';

export const FilesPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const outletContext = useOutletContext<DashboardContextType | null>();

  const cachedTree = repoId ? dashboardCache.getTree(repoId) : null;
  const [treeState, setTreeState] = useState<FetchState>(() => cachedTree ? 'success' : 'idle');
  const [treeNodes, setTreeNodes] = useState<FileNode[]>(() => cachedTree ?? []);
  const [treeError, setTreeError] = useState('');
  const [repository, setRepository] = useState<Repository | null>(
    () => outletContext?.repository || (repoId ? dashboardCache.getRepository(repoId) : null),
  );

  const selectedPath = searchParams.get('path');
  const cachedFile = (repoId && selectedPath) ? dashboardCache.getFile(repoId, selectedPath) : null;
  const [fileState, setFileState] = useState<FetchState>(() => cachedFile ? 'success' : 'idle');
  const [fileContent, setFileContent] = useState(() => cachedFile?.content ?? '');
  const [fileLanguage, setFileLanguage] = useState(() => cachedFile?.language ?? 'plaintext');
  const [fileError, setFileError] = useState('');

  // Sync with shell context when available
  useEffect(() => {
    if (outletContext?.repository) {
      setRepository(outletContext.repository);
    }
  }, [outletContext?.repository]);

  // Highlight lines from citation navigation
  const highlightParam = searchParams.get('lines');
  const highlightLines = React.useMemo<[number, number] | undefined>(() => {
    if (!highlightParam) return undefined;
    const parts = highlightParam.split('-').map(Number);
    if (parts.length === 2 && parts.every((n) => !isNaN(n))) {
      return [parts[0], parts[1]];
    }
    return undefined;
  }, [highlightParam]);

  const highlightRef = useRef<HTMLDivElement | null>(null);

  // Load file tree
  useEffect(() => {
    if (!repoId) return;
    const cached = dashboardCache.getTree(repoId);
    if (cached) {
      setTreeNodes(cached);
      setTreeState('success');
      return;
    }

    const controller = new AbortController();
    let treeRequested = false;
    setTreeState('loading');

    const fetchTree = () => {
      if (treeRequested) return;
      treeRequested = true;
      filesApi.getTree(repoId, { signal: controller.signal }).then((res) => {
        dashboardCache.setTree(repoId, res.tree);
        setTreeNodes(res.tree);
        setTreeState('success');
      }).catch((err) => {
        if (err?.name === 'AbortError') return;
        setTreeError(err instanceof ApiError || err instanceof Error ? err.message : 'Failed to load file tree.');
        setTreeState('error');
      });
    };

    const currentRepo = repository || (repoId ? dashboardCache.getRepository(repoId) : null);
    if (currentRepo && (currentRepo.files_ready || currentRepo.status === 'ready')) {
      fetchTree();
      return () => controller.abort();
    }

    repositoriesApi
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: (data) => {
          setRepository(data);
          dashboardCache.setRepository(repoId, data);
          if (!treeRequested && (data.files_ready || data.status === 'ready')) {
            fetchTree();
          }
        },
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        if (!treeRequested) {
          setTreeError(err instanceof ApiError || err instanceof Error ? err.message : 'Failed to load file tree.');
          setTreeState('error');
        }
      });
    return () => controller.abort();
  }, [repoId, repository]);

  // Load file content when selection changes
  const loadFile = useCallback(
    (path: string) => {
      if (!repoId) return;
      const cached = dashboardCache.getFile(repoId, path);
      if (cached) {
        setFileContent(cached.content);
        setFileLanguage(cached.language);
        setFileState('success');
        setFileError('');
        return;
      }

      setFileState('loading');
      setFileError('');
      filesApi
        .getFile(repoId, path)
        .then((res) => {
          const lang = res.language || 'plaintext';
          dashboardCache.setFile(repoId, path, res.content, lang);
          setFileContent(res.content);
          setFileLanguage(lang);
          setFileState('success');
        })
        .catch((err) => {
          setFileError(
            err instanceof ApiError ? err.message : 'Failed to load file.',
          );
          setFileState('error');
        });
    },
    [repoId],
  );

  // Load file content when selected path in searchParams changes
  useEffect(() => {
    if (selectedPath) {
      loadFile(selectedPath);
    } else {
      setFileState('idle');
      setFileContent('');
      setFileError('');
    }
  }, [selectedPath, loadFile]);

  // Scroll to highlighted line when content loads
  useEffect(() => {
    if (fileState === 'success' && highlightLines) {
      const el = document.getElementById(`L${highlightLines[0]}`);
      if (el) {
        setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    }
  }, [fileState, highlightLines]);

  const handleNodeSelect = (node: FileNode) => {
    setSearchParams({ path: node.path }, { replace: true });
  };

  const handleBreadcrumbNavigate = (path: string) => {
    // Find directory node — only navigate to files
    const flatFind = (nodes: FileNode[], p: string): FileNode | null => {
      for (const n of nodes) {
        if (n.path === p) return n;
        if (n.children) {
          const found = flatFind(n.children, p);
          if (found) return found;
        }
      }
      return null;
    };
    const node = flatFind(treeNodes, path);
    if (node && node.type === 'file') handleNodeSelect(node);
  };

  return (
    <div className="files-page" ref={highlightRef}>
      {repository && repository.status !== 'ready' && (
        <div className={`ingestion-banner ${repository.status === 'failed' ? 'ingestion-banner-error' : ''}`} role={repository.status === 'failed' ? 'alert' : 'status'}>
          {repository.status === 'failed'
            ? `Ingestion failed after the available files were loaded${repository.error ? `: ${repository.error}` : '.'}`
            : `Ingestion in progress: ${repository.status ?? 'starting'}. Files are available while indexing continues.`}
        </div>
      )}
      {/* File Tree */}
      <aside className="file-tree" aria-label="File tree">
        <div className="file-tree-header">Explorer</div>
        <div
          className="file-tree-body"
          role="listbox"
          aria-label="Repository files"
          aria-multiselectable="false"
        >
          {treeState === 'loading' && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}>
              <Spinner size={20} />
            </div>
          )}
          {treeState === 'error' && (
            <p style={{ padding: 'var(--space-4)', fontSize: 'var(--text-meta)', color: 'var(--error)' }}>
              {treeError}
            </p>
          )}
          {treeState === 'success' &&
            treeNodes.map((node) => (
              <TreeNode
                key={node.path}
                node={node}
                depth={0}
                selectedPath={selectedPath}
                onSelect={handleNodeSelect}
              />
            ))}
        </div>
      </aside>

      {/* Right: Breadcrumb + Code Viewer */}
      <div className="file-viewer">
        {selectedPath ? (
          <>
            <Breadcrumb
              path={selectedPath}
              onNavigate={handleBreadcrumbNavigate}
            />
            {fileState === 'loading' && (
              <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-code)' }}>
                <Spinner size={24} />
              </div>
            )}
            {fileState === 'error' && (
              <ErrorState
                title="Could not load file"
                message={fileError}
                style={{ flex: 1, backgroundColor: 'var(--bg-code)' }}
              />
            )}
            {fileState === 'success' && (
              <CodeViewer
                content={fileContent}
                language={fileLanguage}
                highlightLines={highlightLines}
              />
            )}
          </>
        ) : (
          <div className="file-viewer-empty">
            <EmptyState
              icon={<File size={32} />}
              title="Select a file"
              description="Choose a file from the tree to view its contents."
            />
          </div>
        )}
      </div>
    </div>
  );
};
