import React from 'react';
import { FileCode } from 'lucide-react';
import type { Citation } from '../../../api/chat';
import { formatCitationLineRange } from '../../../utils/citations';

interface CitationChipProps {
  citation: Citation;
  onNavigate: (citation: Citation) => void;
}

export const CitationChip: React.FC<CitationChipProps> = ({ citation, onNavigate }) => {
  const fileName = citation.file.split('/').pop() ?? citation.file;
  const lineRange = formatCitationLineRange(citation);

  return (
    <button
      className="citation-chip"
      onClick={() => onNavigate(citation)}
      aria-label={`Navigate to ${citation.file}${lineRange}`}
      title={`${citation.file}${lineRange}`}
    >
      <FileCode size={12} aria-hidden="true" />
      <span className="citation-chip-file">{fileName}</span>
      {lineRange && <span className="citation-chip-lines">{lineRange}</span>}
    </button>
  );
};
