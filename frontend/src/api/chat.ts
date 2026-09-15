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

import { del, get, post } from './client';

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

  sendMessage: async (sessionId: string, content: string) =>
    normalizeMessage(await post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, { content })),

  deleteSessions: (repositoryId: string) =>
    del<void>(`/chat/sessions?repositoryId=${encodeURIComponent(repositoryId)}`),
};
