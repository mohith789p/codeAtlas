import type { ChatMessage, Citation } from '../types';

export function deduplicateCitations(citations: Citation[] = []): Citation[] {
  const seen = new Set<string>();
  return citations.filter((c) => {
    const key = [c.file, c.line_start ?? '', c.line_end ?? ''].join('\0');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function mapBackendCitations(backendCitations: any[] = []): Citation[] {
  return deduplicateCitations(
    backendCitations.map((c) => ({
      file: c.filepath ?? c.file ?? '',
      line_start: c.start_line ?? c.line_start ?? undefined,
      line_end: c.end_line ?? c.line_end ?? undefined,
      symbol: c.symbol || undefined,
      snippet: c.snippet || undefined,
    })),
  );
}

export async function handleStreamResponse(
  res: Response,
  onToken: (token: string) => void,
): Promise<ChatMessage> {
  if (!res.body) throw new Error('Response body is null');
  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalMessage: ChatMessage | null = null;
  let accumulated = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:')) continue;
      const jsonStr = trimmed.slice(5).trim();
      if (!jsonStr) continue;
      try {
        const data = JSON.parse(jsonStr);
        if (data.type === 'token' && typeof data.content === 'string') {
          accumulated += data.content;
          onToken(data.content);
        } else if (data.type === 'done' && data.message) {
          finalMessage = { ...data.message, citations: mapBackendCitations(data.message.citations) };
        }
      } catch { /* ignore chunk error */ }
    }
  }

  return finalMessage || {
    id: `msg-${Date.now()}`,
    role: 'assistant',
    content: accumulated,
    citations: [],
    created_at: new Date().toISOString(),
  };
}
