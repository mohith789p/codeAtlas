import React from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="prose prose-invert prose-indigo max-w-none text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-slate-100 border-b border-slate-800 pb-2 mb-4">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold text-slate-200 mt-6 mb-3 flex items-center space-x-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-md font-semibold text-indigo-300 mt-4 mb-2">{children}</h3>
          ),
          code: ({ inline, className, children, ...props }: any) => {
            if (inline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-xs border border-slate-700"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <pre className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs overflow-x-auto text-slate-200 my-4">
                <code>{children}</code>
              </pre>
            );
          },
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-1.5 my-3 text-slate-300">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1.5 my-3 text-slate-300">{children}</ol>,
          p: ({ children }) => <p className="my-2.5 text-slate-300">{children}</p>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
