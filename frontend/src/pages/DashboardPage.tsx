import React, { useState } from 'react';
import { useRepo } from '../context/RepoContext';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { ChunkResult } from '../types';
import { ConfirmModal } from '../components/ConfirmModal';
import { Database, FileText, Cpu, Search, ArrowRight, MessageSquare, BookOpen, Clock, Sparkles, Trash2 } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { activeRepo, deleteRepository } = useRepo();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchHits, setSearchHits] = useState<ChunkResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRepo || !searchQuery.trim()) return;

    setSearching(true);
    try {
      const res = await api.post<ChunkResult[]>(`/search/${activeRepo.id}`, {
        query: searchQuery,
        top_k: 4,
      });
      setSearchHits(res.data);
    } catch (err) {
      console.error('Vector search failed', err);
    } finally {
      setSearching(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!activeRepo) return;
    setDeleting(true);
    try {
      await deleteRepository(activeRepo.id);
      setShowDeleteModal(false);
    } catch (err: any) {
      console.error('Failed to delete repository:', err);
      setShowDeleteModal(false);
    } finally {
      setDeleting(false);
    }
  };

  if (!activeRepo) {
    return (
      <div className="p-8 text-center flex flex-col items-center justify-center h-[calc(100vh-8rem)]">
        <Database className="w-16 h-16 text-indigo-400 mb-4 opacity-50 animate-bounce" />
        <h2 className="text-xl font-bold text-slate-200">No Active Repository Selected</h2>
        <p className="text-sm text-slate-400 mt-2 max-w-md">
          Upload a ZIP repository from the top header to begin semantic analysis and RAG exploration.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="p-8 space-y-8 max-w-7xl mx-auto">
        {/* Header Banner */}
        <div className="glass-panel p-8 rounded-2xl border border-slate-800 relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="absolute right-0 top-0 w-96 h-full bg-gradient-to-l from-indigo-600/10 to-transparent pointer-events-none" />
          <div className="relative z-10">
            <div className="flex items-center space-x-3 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
              <Sparkles className="w-4 h-4" />
              <span>Repository Ingested</span>
            </div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">{activeRepo.name}</h1>
            <p className="text-sm text-slate-400 mt-2 max-w-2xl">
              Knowledge base compiled. Code parsed into vector embeddings for semantic retrieval.
            </p>

            <div className="mt-6 flex flex-wrap gap-4">
              <div className="px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center space-x-3">
                <FileText className="w-4 h-4 text-indigo-400" />
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-semibold">Total Files</p>
                  <p className="text-sm font-bold text-slate-200">{activeRepo.file_count}</p>
                </div>
              </div>

              <div className="px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center space-x-3">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-semibold">Code Chunks</p>
                  <p className="text-sm font-bold text-slate-200">{activeRepo.chunk_count}</p>
                </div>
              </div>

              <div className="px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center space-x-3">
                <Clock className="w-4 h-4 text-emerald-400" />
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-semibold">Status</p>
                  <p className="text-sm font-bold text-emerald-400 uppercase text-xs">{activeRepo.status}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Delete Repo Button */}
          <div className="relative z-10 flex-shrink-0">
            <button
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:text-rose-200 font-medium text-xs flex items-center space-x-2 transition"
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete Repo</span>
            </button>
          </div>
        </div>

        {/* Quick Action Navigation Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div onClick={() => navigate('/explorer')} className="glass-card p-6 rounded-2xl cursor-pointer group">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-200">Repository Explorer</h3>
            <p className="text-xs text-slate-400 mt-1">Browse hierarchical directory structure & inspect raw source code.</p>
            <div className="mt-4 text-xs font-semibold text-indigo-400 flex items-center space-x-1 group-hover:translate-x-1 transition">
              <span>Launch Explorer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          <div onClick={() => navigate('/chat')} className="glass-card p-6 rounded-2xl cursor-pointer group">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <MessageSquare className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-200">AI RAG Chat Assistant</h3>
            <p className="text-xs text-slate-400 mt-1">Ask questions about functions, architecture, and code logic.</p>
            <div className="mt-4 text-xs font-semibold text-cyan-400 flex items-center space-x-1 group-hover:translate-x-1 transition">
              <span>Open Chat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          <div onClick={() => navigate('/docs')} className="glass-card p-6 rounded-2xl cursor-pointer group">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-200">Doc Generator</h3>
            <p className="text-xs text-slate-400 mt-1">Generate automated README files & Architecture specifications.</p>
            <div className="mt-4 text-xs font-semibold text-emerald-400 flex items-center space-x-1 group-hover:translate-x-1 transition">
              <span>Generate Docs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>

        {/* Semantic Vector Search */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h2 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
            <Search className="w-5 h-5 text-indigo-400" />
            <span>Semantic Vector Search</span>
          </h2>
          <form onSubmit={handleSearch} className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. How does authentication token validation work?"
              className="flex-1 bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
            <button
              type="submit"
              disabled={searching}
              className="gradient-btn px-5 py-2.5 rounded-xl text-sm flex items-center space-x-2 disabled:opacity-50"
            >
              {searching ? <span>Searching...</span> : <span>Search Chunks</span>}
            </button>
          </form>

          {searchHits.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {searchHits.map((hit) => (
                <div key={hit.id} className="glass-card p-4 rounded-xl space-y-2 border border-slate-800">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-indigo-300 font-semibold">{hit.file_path}</span>
                    <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono text-[10px]">
                      Match Score: {(hit.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
                    Lines {hit.start_line} - {hit.end_line}
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950/90 text-xs font-mono text-slate-300 overflow-x-auto border border-slate-800/80">
                    {hit.content.length > 300 ? hit.content.substring(0, 300) + '...' : hit.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Confirm Delete Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        title="Delete Repository"
        message={`Are you sure you want to permanently delete "${activeRepo.name}"? All associated files, embeddings, chat history, and generated docs will be removed. This action cannot be undone.`}
        confirmLabel="Delete Repository"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowDeleteModal(false)}
      />
    </>
  );
};
