import React from 'react';
import { FileDetail } from '../types';
import { FileCode, Hash, Copy, Check } from 'lucide-react';

interface CodeViewerProps {
  file: FileDetail | null;
  highlightRange?: { start: number; end: number };
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ file, highlightRange }) => {
  const [copied, setCopied] = React.useState(false);

  if (!file) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm">
        <FileCode className="w-12 h-12 mb-3 text-slate-600" />
        <p>Select a file from the repository tree to inspect source code.</p>
      </div>
    );
  }

  const lines = file.content.split('\n');

  const copyToClipboard = () => {
    navigator.clipboard.writeText(file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-full flex flex-col glass-panel rounded-xl overflow-hidden border border-slate-800">
      {/* File Header */}
      <div className="px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileCode className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-mono font-medium text-slate-200">{file.path}</span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
            {(file.size_bytes / 1024).toFixed(1)} KB
          </span>
        </div>
        <button
          onClick={copyToClipboard}
          className="flex items-center space-x-1 text-xs text-slate-400 hover:text-slate-200 transition"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Editor Body */}
      <div className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const isHighlighted =
                highlightRange &&
                lineNum >= highlightRange.start &&
                lineNum <= highlightRange.end;

              return (
                <tr
                  key={idx}
                  className={`hover:bg-slate-800/40 transition ${
                    isHighlighted ? 'bg-indigo-600/20 text-indigo-200 font-semibold' : ''
                  }`}
                >
                  <td className="w-12 text-right pr-4 text-slate-600 select-none py-0.5">
                    {lineNum}
                  </td>
                  <td className="whitespace-pre text-slate-300 py-0.5">{line || ' '}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
