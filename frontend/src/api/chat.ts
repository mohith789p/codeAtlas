/**
 * Chat API
 *
 * Required endpoints (backend dependency):
 *
 * GET  /api/chat/sessions?repositoryId=:id
 *   response: ChatSession[]
 *
 * POST /api/chat/sessions?repositoryId=:id
 *   response: ChatSession
 *
 * GET  /api/chat/sessions/:sessionId/messages
 *   response: ChatMessage[]
 *
 * POST /api/chat/sessions/:sessionId/messages
 *   body: { content: string }
 *   response: ChatMessage (AI response with optional citations)
 */

import { API_BASE, ApiError, del, get, post } from './client';

export interface Citation {
  file: string;
  line_start?: number;
  line_end?: number;
  symbol?: string;
  chunk_id?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  created_at: string;
  updated_at?: string;
}

export function deduplicateCitations(citations: Citation[] = []): Citation[] {
  const seen = new Set<string>();
  return citations.filter((citation) => {
    const identity = [citation.file, citation.line_start ?? '', citation.line_end ?? ''].join('\u0000');
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

function normalizeMessage(message: ChatMessage): ChatMessage {
  return message.citations
    ? { ...message, citations: deduplicateCitations(message.citations) }
    : message;
}

export const chatApi = {
  getSessions: (repositoryId: string, opts?: RequestInit) =>
    get<ChatSession[]>(`/chat/sessions?repositoryId=${encodeURIComponent(repositoryId)}`, opts),

  createSession: (repositoryId: string, opts?: RequestInit) =>
    post<ChatSession>(`/chat/sessions?repositoryId=${encodeURIComponent(repositoryId)}`, undefined, opts),

  getMessages: async (sessionId: string, opts?: RequestInit) =>
    (await get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, opts)).map(normalizeMessage),

  // Deprecated / Unused: Replaced by streamMessage below. Kept orphaned for backward compatibility.
  sendMessage: async (sessionId: string, content: string) =>
    normalizeMessage(await post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, { content })),

  streamMessage: async (
    sessionId: string,
    content: string,
    onToken: (token: string) => void,
    signal?: AbortSignal,
  ): Promise<ChatMessage> => {
    const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
      signal,
    });

    if (!response.ok) {
      let errDetail = 'Failed to stream response.';
      try {
        const errJson = await response.json();
        errDetail = errJson.detail || errJson.message || errDetail;
      } catch { /* ignore */ }
      throw new ApiError(response.status, errDetail);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let completedMessage: ChatMessage | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const jsonStr = trimmed.slice(6).trim();
        if (!jsonStr) continue;

        try {
          const event = JSON.parse(jsonStr);
          if (event.type === 'token' && typeof event.content === 'string') {
            onToken(event.content);
          } else if (event.type === 'done' && event.message) {
            completedMessage = normalizeMessage(event.message);
          } else if (event.type === 'error') {
            throw new Error(event.error || 'Streaming generation failed.');
          }
        } catch (parseErr) {
          if (parseErr instanceof Error && (parseErr.message.includes('Streaming generation failed.') || (event && event.type === 'error'))) {
            throw parseErr;
          }
          console.warn('[streamMessage] Failed to parse SSE event:', jsonStr, parseErr);
        }
      }
    }

    if (!completedMessage) {
      throw new Error('Stream ended without completion message');
    }

    return completedMessage;
  },

  deleteSessions: (repositoryId: string) =>
    del<void>(`/chat/sessions?repositoryId=${encodeURIComponent(repositoryId)}`),
};
