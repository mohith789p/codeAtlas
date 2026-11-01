import type { Citation } from '../../features/chat/types';

/**
 * Strips raw inline citation text from model output so it can be rendered
 * cleanly as UI chips without cluttering the markdown text.
 */
export function stripCitationMetadata(content: string, citations: Citation[] = []): string {
  if (!content) return '';

  const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  const citationPatterns = (citations || []).flatMap((citation) => {
    if (!citation.file) return [];
    const file = escapeRegex(citation.file);
    const basename = file.split('/').pop() ?? file;
    const end = citation.line_end ?? citation.line_start;
    const range = citation.line_start !== undefined
      ? (end && end !== citation.line_start
          ? `[:#]L?${citation.line_start}[-–]L?${end}`
          : `[:#]L?${citation.line_start}`)
      : '(?:[:#]L?\\d+(?:[-–]L?\\d+)?)?';
    const symbol = citation.symbol
      ? `(?:[ \\t]+(?:\\(${escapeRegex(citation.symbol)}\\)|${escapeRegex(citation.symbol)}))?`
      : `(?:[ \\t]+\\([A-Za-z_][A-Za-z0-9_.]*\\))?`;

    return [
      `\\[[ \\t]*\\x60?(?:${file}|${basename})${range}${symbol}[ \\t]*\\x60?[ \\t]*\\]`,
      `[ \\t]*\\x60?(?:${file}|${basename})${range}${symbol}[ \\t]*\\x60?`,
    ];
  });

  // Generic bracketed citation pattern supporting single or comma/semicolon-separated citations:
  // e.g. [README.md:37, main.py:14-16], [src/app.py:10-20], [`README.md`]
  const item = '\\x60?[a-zA-Z0-9_\\-./\\\\]+(?:[:#]L?\\d+(?:[-–]L?\\d+)?)?(?:[ \\t]+\\([A-Za-z0-9_.]+\\))?\\x60?';
  const genericCitation = `\\[[ \\t]*${item}(?:[ \\t]*[,;][ \\t]*${item})*[ \\t]*\\]`;
  // Empty brackets left behind: [], [ ], [, ], etc.
  const emptyBrackets = '\\[[ \\t,;]*\\]';

  const pattern = new RegExp([...citationPatterns, genericCitation, emptyBrackets].join('|'), 'g');

  return content
    .split(/(```[\s\S]*?```)/g)
    .map((part, index) => {
      if (index % 2 === 1) return part; // Keep fenced code blocks untouched
      return part
        .replace(pattern, '')
        .replace(/\[[ \t,;]*\]/g, '') // Ensure any remaining empty brackets are stripped
        .replace(/[ \t]+([.,;:!?])/g, '$1') // Prevent orphan space before punctuation (e.g. "events ." -> "events.")
        .replace(/[ \t]{2,}/g, ' ');
    })
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
