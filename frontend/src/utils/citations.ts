import type { Citation } from '../api/chat';

/**
 * Strips raw inline citation text from model output so it can be rendered
 * cleanly as UI chips without cluttering the markdown text.
 */
export function stripCitationMetadata(content: string, citations: Citation[]): string {
  if (!citations.length) return content;

  const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  const citationPatterns = citations.flatMap((citation) => {
    if (!citation.file || citation.line_start === undefined) return [];
    const file = escapeRegex(citation.file);
    const basename = file.split('/').pop() ?? file;
    const end = citation.line_end ?? citation.line_start;
    const range =
      citation.line_start === end
        ? `${citation.line_start}`
        : `${citation.line_start}[-–]${end}`;
    const symbol = citation.symbol
      ? `(?:[ \\t]+(?:\\(${escapeRegex(citation.symbol)}\\)|${escapeRegex(citation.symbol)}))?`
      : `(?:[ \\t]+\\([A-Za-z_][A-Za-z0-9_.]*\\))?`;
    return [`[ \\t]*\\x60?(?:${file}|${basename}):${range}${symbol}[ \\t]*\\x60?`];
  });

  if (!citationPatterns.length) return content;
  const pattern = new RegExp(citationPatterns.join('|'), 'g');
  return content
    .split(/(```[\s\S]*?```)/g)
    .map((part, index) => (index % 2 === 1 ? part : part.replace(pattern, '')))
    .join('')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * Format a line range string from a Citation object.
 */
export function formatCitationLineRange(citation: Citation): string {
  if (!citation.line_start) return '';
  if (citation.line_end && citation.line_end !== citation.line_start) {
    return `:${citation.line_start}–${citation.line_end}`;
  }
  return `:${citation.line_start}`;
}
