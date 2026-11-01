import React, { useMemo } from 'react';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import { FileBreadcrumb } from './FileBreadcrumb';
import './CodeViewer.css';

interface CodeViewerProps {
  path: string;
  content: string;
  language: string;
  highlightLines?: [number, number];
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  path,
  content,
  language,
  highlightLines,
}) => {
  const highlightedLines = useMemo(() => {
    try {
      const validLang = hljs.getLanguage(language) ? language : 'plaintext';
      return hljs.highlight(content, { language: validLang }).value.split('\n');
    } catch {
      return content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').split('\n');
    }
  }, [content, language]);

  return (
    <div className="file-viewer" role="region" aria-label="Code viewer">
      <FileBreadcrumb
        path={path}
        language={language}
        lineCount={highlightedLines.length}
        content={content}
      />
      <div className="code-viewer-container">
        {highlightedLines.map((lineHtml, idx) => {
          const lineNum = idx + 1;
          const isHighlighted = highlightLines && lineNum >= highlightLines[0] && lineNum <= highlightLines[1];

          return (
            <div
              key={lineNum}
              id={`L${lineNum}`}
              className={`code-line ${isHighlighted ? 'code-line-highlighted' : ''}`}
            >
              <span className="code-line-number" aria-hidden="true">{lineNum}</span>
              <span
                className="code-line-content"
                dangerouslySetInnerHTML={{ __html: lineHtml || ' ' }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
