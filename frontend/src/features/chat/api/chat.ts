import { get, post, del, API_BASE, ApiError } from '../../../services/api/client';
import { dashboardCache } from '../../../services/api/cache';
import type { Citation, ChatMessage, ChatSession, GenerationResponse, QueryOptions } from '../types';

export function deduplicateCitations(citations: Citation[] = []): Citation[] {
  const seen = new Set<string>();
  return citations.filter((citation) => {
    const identity = [citation.file, citation.line_start ?? '', citation.line_end ?? ''].join('\u0000');
    if (seen.has(identity)) return false;
    seen.add(identity);
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

export const chatApi = {
  submitQuery: (repositoryId: string, query: string, options?: QueryOptions, opts?: RequestInit) =>
    post<GenerationResponse>(
      '/queries',
      {
        repository_id: repositoryId,
        query,
        options: options || {},
      },
      opts,
    ),

  getSessions: async (repositoryId: string, opts?: RequestInit): Promise<ChatSession[]> => {
    try {
      const sessions = await get<ChatSession[]>(`/chat/sessions?repository_id=${encodeURIComponent(repositoryId)}`, opts);
      if (sessions && sessions.length > 0) {
        return sessions;
      }
    } catch {
      // Graceful fallback to cache if backend is unreachable
    }
    const cached = dashboardCache.getSessionId(repositoryId);
    if (cached) {
      return [{ id: cached, repository_id: repositoryId, created_at: new Date().toISOString() }];
    }
    return [];
  },

  createSession: async (repositoryId: string, opts?: RequestInit): Promise<ChatSession> => {
    try {
      const session = await post<ChatSession>('/chat/sessions', { repository_id: repositoryId }, opts);
      if (session) {
        dashboardCache.setSessionId(repositoryId, session.id);
        return session;
      }
    } catch {
      // Graceful fallback
    }
    const fallbackId = `session-${Date.now()}`;
    dashboardCache.setSessionId(repositoryId, fallbackId);
    return { id: fallbackId, repository_id: repositoryId, created_at: new Date().toISOString() };
  },

  getMessages: async (sessionId: string, opts?: RequestInit): Promise<ChatMessage[]> => {
    try {
      const messages = await get<ChatMessage[]>(`/chat/sessions/${encodeURIComponent(sessionId)}/messages`, opts);
      return messages.map((m) => ({
        ...m,
        citations: mapBackendCitations(m.citations),
      }));
    } catch {
      return [];
    }
  },

  sendMessage: async (repositoryId: string, content: string): Promise<ChatMessage> => {
    const response = await chatApi.submitQuery(repositoryId, content);
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: response.answer,
      citations: mapBackendCitations(response.citations),
      created_at: new Date().toISOString(),
    };
  },

  streamMessage: async (
    repositoryId: string,
    content: string,
    onToken: (token: string) => void,
    signal?: AbortSignal,
    sessionId?: string | null,
  ): Promise<ChatMessage> => {
    const activeSessionId = sessionId || dashboardCache.getSessionId(repositoryId) || undefined;

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_id: repositoryId,
          content,
          session_id: activeSessionId,
        }),
        signal,
      });

      if (!res.ok) {
        let errorDetail: string | undefined;
        try {
          const errBody = await res.json();
          errorDetail = errBody.detail || errBody.message;
        } catch {
          // ignore
        }
        throw new ApiError(res.status, errorDetail || `Request failed with status ${res.status}`);
      }

      if (!res.body) {
        throw new Error('Response body is null');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let finalMessage: ChatMessage | null = null;
      let accumulatedContent = '';

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
              accumulatedContent += data.content;
              onToken(data.content);
            } else if (data.type === 'done' && data.message) {
              finalMessage = {
                ...data.message,
                citations: mapBackendCitations(data.message.citations),
              };
            }
          } catch {
            // Ignore malformed SSE chunks
          }
        }
      }

      if (finalMessage) {
        return finalMessage;
      }

      return {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: accumulatedContent,
        citations: [],
        created_at: new Date().toISOString(),
      };
    } catch (streamErr) {
      // If streaming fetch fails (e.g., endpoint unavailable), fall back to submitQuery
      if (signal?.aborted) throw streamErr;
      const response = await chatApi.submitQuery(repositoryId, content, undefined, { signal });
      if (response.answer) {
        onToken(response.answer);
      }
      return {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        citations: mapBackendCitations(response.citations),
        created_at: new Date().toISOString(),
      };
    }
  },

  deleteSessions: async (repositoryId: string, opts?: RequestInit): Promise<void> => {
    dashboardCache.clear(repositoryId);
    try {
      await del<void>(`/chat/sessions?repository_id=${encodeURIComponent(repositoryId)}`, opts);
    } catch {
      // Ignore cleanup error
    }
  },
};
