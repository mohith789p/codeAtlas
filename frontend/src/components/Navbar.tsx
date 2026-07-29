import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRepo } from '../context/RepoContext';
import { UploadModal } from './UploadModal';
import { ConfirmModal } from './ConfirmModal';
import { Layers, Upload, LogOut, ChevronDown, Database, Trash2 } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { repositories, activeRepo, setActiveRepo, deleteRepository } = useRepo();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isRepoDropdownOpen, setIsRepoDropdownOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{ id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDeleteClick = (e: React.MouseEvent, repoId: number, repoName: string) => {
    e.stopPropagation();
    setIsRepoDropdownOpen(false);
    setConfirmTarget({ id: repoId, name: repoName });
  };

  const handleConfirmDelete = async () => {
    if (!confirmTarget) return;
    setDeleting(true);
    try {
      await deleteRepository(confirmTarget.id);
    } catch (err) {
      console.error('Failed to delete repository:', err);
    } finally {
      setDeleting(false);
      setConfirmTarget(null);
    }
  };

  return (
    <>
      <header className="h-16 border-b border-slate-800/80 bg-dark-900/90 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-dark-900 rounded-[10px] flex items-center justify-center">
              <Layers className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight gradient-text">CodeAtlas</span>
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                RAG Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">Developer Knowledge Platform</p>
          </div>
        </div>

        {/* Repository Selector */}
        {user && (
          <div className="flex items-center space-x-4">
            <div className="relative">
              <button
                onClick={() => setIsRepoDropdownOpen(!isRepoDropdownOpen)}
                className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-sm font-medium hover:bg-slate-800 hover:border-slate-600 transition"
              >
                <Database className="w-4 h-4 text-indigo-400" />
                <span className="max-w-[160px] truncate text-slate-200">
                  {activeRepo ? activeRepo.name : 'Select Repository'}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {isRepoDropdownOpen && (
                <div className="absolute right-0 mt-2 w-72 glass-panel rounded-xl shadow-2xl py-2 border border-slate-700/80 z-50">
                  <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Repositories ({repositories.length})
                  </div>
                  <div className="max-h-60 overflow-y-auto">
                    {repositories.length === 0 ? (
                      <div className="px-4 py-3 text-xs text-slate-500 text-center">
                        No repositories uploaded yet.
                      </div>
                    ) : (
                      repositories.map((repo) => (
                        <div
                          key={repo.id}
                          onClick={() => {
                            setActiveRepo(repo);
                            setIsRepoDropdownOpen(false);
                          }}
                          className={`w-full px-3 py-2 text-sm flex items-center justify-between cursor-pointer hover:bg-indigo-600/10 hover:text-indigo-300 transition ${
                            activeRepo?.id === repo.id ? 'bg-indigo-600/20 text-indigo-400 font-medium' : 'text-slate-300'
                          }`}
                        >
                          <span className="truncate max-w-[130px]">{repo.name}</span>
                          <div className="flex items-center space-x-2">
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded ${
                                repo.status === 'ready'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : repo.status === 'processing'
                                  ? 'bg-amber-500/20 text-amber-400 animate-pulse'
                                  : 'bg-rose-500/20 text-rose-400'
                              }`}
                            >
                              {repo.status}
                            </span>
                            <button
                              onClick={(e) => handleDeleteClick(e, repo.id, repo.name)}
                              title="Delete Repository"
                              className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/20 transition"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Upload Button */}
            <button
              onClick={() => setIsUploadOpen(true)}
              className="gradient-btn px-3.5 py-1.5 rounded-lg text-sm flex items-center space-x-1.5"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Repo</span>
            </button>

            {/* User Avatar & Logout */}
            <div className="flex items-center space-x-3 pl-2 border-l border-slate-800">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-indigo-400 text-xs">
                {user.email.substring(0, 2).toUpperCase()}
              </div>
              <button
                onClick={logout}
                title="Logout"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </header>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />

      <ConfirmModal
        isOpen={!!confirmTarget}
        title="Delete Repository"
        message={`Are you sure you want to permanently delete "${confirmTarget?.name}"? All files, embeddings, chat history, and generated docs will be removed. This cannot be undone.`}
        confirmLabel="Delete Repository"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmTarget(null)}
      />
    </>
  );
};
