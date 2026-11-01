import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { File } from 'lucide-react';
import { filesApi } from '../api/files';
import type { FileNode } from '../types';
import { dashboardCache } from '../../../services/api/cache';
import { Spinner, EmptyState, ErrorState } from '../../../shared/components/ui/States';
import { FileTree } from '../components/FileTree';
import { CodeViewer } from '../components/CodeViewer';
import './FilesPage.css';

export const FilesPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const cachedTree = repoId ? dashboardCache.getTree(repoId) : null;
  const [treeNodes, setTreeNodes] = useState<FileNode[]>(() => cachedTree ?? []);
  const [treeLoading, setTreeLoading] = useState(!cachedTree);
  const [treeError, setTreeError] = useState('');

  const selectedPath = searchParams.get('path');
  const cachedFile = (repoId && selectedPath) ? dashboardCache.getFile(repoId, selectedPath) : null;
  const [fileContent, setFileContent] = useState(() => cachedFile?.content ?? '');
  const [fileLanguage, setFileLanguage] = useState(() => cachedFile?.language ?? 'plaintext');
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState('');

  const highlightParam = searchParams.get('lines');
  const highlightLines = React.useMemo<[number, number] | undefined>(() => {
    if (!highlightParam) return undefined;
    const parts = highlightParam.split('-').map(Number);
    return (parts.length === 2 && parts.every((n) => !isNaN(n))) ? [parts[0], parts[1]] : undefined;
  }, [highlightParam]);

  useEffect(() => {
    if (!repoId || cachedTree) return;
    const controller = new AbortController();
    filesApi.getTree(repoId, { signal: controller.signal })
      .then((res) => {
        dashboardCache.setTree(repoId, res.tree);
        setTreeNodes(res.tree);
        setTreeLoading(false);
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        setTreeError('Failed to load file tree.');
        setTreeLoading(false);
      });
    return () => controller.abort();
  }, [repoId, cachedTree]);

  const loadFile = useCallback((path: string) => {
    if (!repoId) return;
    const cached = dashboardCache.getFile(repoId, path);
    if (cached) {
      setFileContent(cached.content);
      setFileLanguage(cached.language);
      return;
    }
    setFileLoading(true);
    setFileError('');
    filesApi.getFile(repoId, path)
      .then((res) => {
        const lang = res.language || 'plaintext';
        dashboardCache.setFile(repoId, path, res.content, lang);
        setFileContent(res.content);
        setFileLanguage(lang);
        setFileLoading(false);
      })
      .catch(() => {
        setFileError('Failed to load file contents.');
        setFileLoading(false);
      });
  }, [repoId]);

  useEffect(() => {
    if (selectedPath) loadFile(selectedPath);
  }, [selectedPath, loadFile]);

  useEffect(() => {
    if (highlightLines) {
      const el = document.getElementById(`L${highlightLines[0]}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightLines, fileContent]);

  return (
    <div className="files-page">
      <FileTree
        nodes={treeNodes}
        selectedPath={selectedPath}
        onSelect={(node) => setSearchParams({ path: node.path }, { replace: true })}
        loading={treeLoading}
        error={treeError}
      />
      {selectedPath ? (
        fileLoading ? (
          <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', background: 'var(--bg-code)' }}>
            <Spinner size={24} />
          </div>
        ) : fileError ? (
          <ErrorState title="Could not load file" message={fileError} style={{ flex: 1, background: 'var(--bg-code)' }} />
        ) : (
          <CodeViewer path={selectedPath} content={fileContent} language={fileLanguage} highlightLines={highlightLines} />
        )
      ) : (
        <div className="file-viewer-empty">
          <EmptyState icon={<File size={28} />} title="Select a file" description="Choose any file from the explorer to inspect syntax and symbols." />
        </div>
      )}
    </div>
  );
};
