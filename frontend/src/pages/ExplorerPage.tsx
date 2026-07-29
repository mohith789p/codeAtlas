import React, { useEffect, useState } from 'react';
import { useRepo } from '../context/RepoContext';
import api from '../api/client';
import { FileNode, FileDetail } from '../types';
import { FileTreeItem } from '../components/FileTree';
import { CodeViewer } from '../components/CodeViewer';
import { FolderTree, Search, Loader2 } from 'lucide-react';

export const ExplorerPage: React.FC = () => {
  const { activeRepo } = useRepo();
  const [treeData, setTreeData] = useState<FileNode | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<number | undefined>();
  const [selectedFile, setSelectedFile] = useState<FileDetail | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);

  useEffect(() => {
    if (!activeRepo) return;
    const fetchTree = async () => {
      setLoadingTree(true);
      try {
        const res = await api.get(`/repositories/${activeRepo.id}/tree`);
        setTreeData(res.data);
      } catch (err) {
        console.error('Failed to fetch file tree', err);
      } finally {
        setLoadingTree(false);
      }
    };
    fetchTree();
  }, [activeRepo]);

  const handleSelectFile = async (fileId: number) => {
    if (!activeRepo) return;
    setSelectedFileId(fileId);
    setLoadingFile(true);
    try {
      const res = await api.get<FileDetail>(`/repositories/${activeRepo.id}/files/${fileId}`);
      setSelectedFile(res.data);
    } catch (err) {
      console.error('Failed to load file content', err);
    } finally {
      setLoadingFile(false);
    }
  };

  if (!activeRepo) {
    return (
      <div className="p-8 text-center text-slate-400">
        Please select or upload a repository from the top bar.
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] p-6 flex gap-6 overflow-hidden">
      {/* File Tree Sidebar */}
      <div className="w-80 glass-panel rounded-2xl p-4 flex flex-col border border-slate-800 flex-shrink-0">
        <div className="flex items-center space-x-2 pb-3 mb-3 border-b border-slate-800 text-xs font-semibold uppercase text-slate-400">
          <FolderTree className="w-4 h-4 text-indigo-400" />
          <span>Repository Files</span>
        </div>

        <div className="flex-1 overflow-y-auto pr-1">
          {loadingTree ? (
            <div className="flex items-center justify-center h-32 text-slate-500 text-xs">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-400 mr-2" />
              <span>Parsing File Tree...</span>
            </div>
          ) : treeData ? (
            <FileTreeItem
              node={treeData}
              onSelectFile={handleSelectFile}
              selectedFileId={selectedFileId}
            />
          ) : (
            <div className="text-xs text-slate-500 p-4">No file structure found.</div>
          )}
        </div>
      </div>

      {/* Main Code View Area */}
      <div className="flex-1 h-full overflow-hidden">
        {loadingFile ? (
          <div className="h-full glass-panel rounded-2xl flex items-center justify-center text-slate-400 text-sm">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mr-2" />
            <span>Fetching source content...</span>
          </div>
        ) : (
          <CodeViewer file={selectedFile} />
        )}
      </div>
    </div>
  );
};
