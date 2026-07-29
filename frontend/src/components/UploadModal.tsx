import React, { useState, useCallback } from 'react';
import api from '../api/client';
import { useRepo } from '../context/RepoContext';
import { Upload, X, FileArchive, CheckCircle2, AlertCircle } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose }) => {
  const { fetchRepositories, setActiveRepo } = useRepo();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  if (!isOpen) return null;

  const validateAndSetFile = (selected: File) => {
    if (!selected.name.endsWith('.zip')) {
      setError('Please select a valid .zip repository file.');
      setFile(null);
      return;
    }
    if (selected.size > 200 * 1024 * 1024) {
      setError('File exceeds maximum size of 200 MB.');
      setFile(null);
      return;
    }
    setError(null);
    setFile(selected);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) validateAndSetFile(e.target.files[0]);
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) validateAndSetFile(dropped);
  }, []);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/repositories/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccessMsg(`"${res.data.name}" uploaded! Background indexing started.`);
      await fetchRepositories();
      setActiveRepo(res.data);
      setTimeout(() => {
        setUploading(false);
        setSuccessMsg(null);
        setFile(null);
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFile(null);
      setError(null);
      setSuccessMsg(null);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={handleClose} />

      <div className="relative glass-panel w-full max-w-md rounded-2xl p-6 border border-slate-700 shadow-2xl animate-fade-in">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">Upload Repository</h3>
            <p className="text-xs text-slate-400">Upload a project ZIP file to index and embed</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2 animate-slide-up">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2 animate-slide-up">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-indigo-500 bg-indigo-600/10 scale-[1.01]'
              : 'border-slate-700 hover:border-indigo-500/50 bg-slate-900/40'
          }`}
        >
          <input
            type="file"
            accept=".zip"
            onChange={handleFileChange}
            className="hidden"
            id="repo-zip-input"
          />
          <label htmlFor="repo-zip-input" className="cursor-pointer block">
            <FileArchive className={`w-10 h-10 mx-auto mb-3 transition ${isDragging ? 'text-indigo-400 scale-110' : 'text-indigo-400/60'}`} />
            {file ? (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-indigo-300">{file.name}</p>
                <p className="text-xs text-slate-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                <p className="text-[11px] text-slate-500 mt-1">Click to change file</p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-slate-300">
                  {isDragging ? 'Drop your ZIP here' : 'Drop ZIP here or click to browse'}
                </p>
                <p className="text-xs text-slate-500 mt-1">Max 200 MB · .zip repositories only</p>
              </div>
            )}
          </label>
        </div>

        {/* Upload progress bar (shown while uploading) */}
        {uploading && !successMsg && (
          <div className="mt-4">
            <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-indigo-600 to-violet-600 rounded-full animate-pulse w-full" />
            </div>
            <p className="text-[11px] text-slate-500 text-center mt-2">Uploading & scheduling background indexing…</p>
          </div>
        )}

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={handleClose}
            disabled={uploading}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="gradient-btn px-5 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Uploading…</span>
              </>
            ) : (
              <span>Start Ingestion</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
