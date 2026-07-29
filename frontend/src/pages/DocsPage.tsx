import React, { useState, useEffect } from 'react';
import { useRepo } from '../context/RepoContext';
import api from '../api/client';
import { GeneratedDoc } from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { BookOpen, Sparkles, FileText, Cpu, Loader2, Copy, Check } from 'lucide-react';

export const DocsPage: React.FC = () => {
  const { activeRepo } = useRepo();
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<GeneratedDoc | null>(null);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchDocs = async () => {
    if (!activeRepo) return;
    try {
      const res = await api.get<GeneratedDoc[]>(`/docs/${activeRepo.id}`);
      setDocs(res.data);
      if (res.data.length > 0 && !selectedDoc) {
        setSelectedDoc(res.data[0]);
      }
    } catch (err) {
      console.error('Failed to load documentation', err);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [activeRepo]);

  const handleGenerate = async (docType: 'readme' | 'architecture') => {
    if (!activeRepo || generating) return;
    setGenerating(true);

    try {
      const res = await api.post<GeneratedDoc>('/docs/generate', {
        repo_id: activeRepo.id,
        doc_type: docType,
      });
      setDocs([res.data, ...docs]);
      setSelectedDoc(res.data);
    } catch (err) {
      console.error('Doc generation failed', err);
    } finally {
      setGenerating(false);
    }
  };

  const copyDocToClipboard = () => {
    if (!selectedDoc) return;
    navigator.clipboard.writeText(selectedDoc.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!activeRepo) {
    return (
      <div className="p-8 text-center text-slate-400">
        Please select or upload a repository to manage documentation.
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] p-6 flex gap-6 overflow-hidden">
      {/* Sidebar Controls */}
      <div className="w-80 glass-panel rounded-2xl p-6 flex flex-col border border-slate-800 flex-shrink-0 space-y-6">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold uppercase text-slate-400 mb-2">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <span>Generate Documentation</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Generate production-ready markdown specifications directly from analyzed repository code.
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => handleGenerate('readme')}
            disabled={generating}
            className="gradient-btn w-full py-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
            <span>Generate README.md</span>
          </button>

          <button
            onClick={() => handleGenerate('architecture')}
            disabled={generating}
            className="w-full py-3 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-indigo-300 flex items-center justify-center space-x-2 transition disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Cpu className="w-4 h-4 text-cyan-400" />
            )}
            <span>Generate Architecture Specification</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pt-4 border-t border-slate-800">
          <div className="text-[11px] font-semibold uppercase text-slate-500 tracking-wider mb-3">
            Generated Documents ({docs.length})
          </div>

          <div className="space-y-2">
            {docs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                  selectedDoc?.id === doc.id
                    ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300'
                    : 'bg-slate-900/50 border-slate-800/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className="font-semibold uppercase tracking-wider text-[10px] text-indigo-400 mb-1">
                  {doc.doc_type}
                </div>
                <div className="text-[10px] text-slate-500">
                  {new Date(doc.created_at).toLocaleDateString()} at{' '}
                  {new Date(doc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Document Viewer */}
      <div className="flex-1 glass-panel rounded-2xl flex flex-col border border-slate-800 overflow-hidden">
        {selectedDoc ? (
          <div className="h-full flex flex-col">
            {/* Action Bar */}
            <div className="px-6 py-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span className="font-bold text-slate-200 uppercase">{selectedDoc.doc_type} Document</span>
              </div>

              <button
                onClick={copyDocToClipboard}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300 hover:text-white transition"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Markdown</span>
                  </>
                )}
              </button>
            </div>

            {/* Document Content */}
            <div className="flex-1 overflow-y-auto p-8">
              <MarkdownRenderer content={selectedDoc.content} />
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm space-y-2">
            <BookOpen className="w-12 h-12 text-slate-600 mb-2" />
            <p>Select or generate a document to view Markdown report.</p>
          </div>
        )}
      </div>
    </div>
  );
};
