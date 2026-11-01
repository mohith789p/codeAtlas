import { get, post, del, API_BASE, ApiError } from '../../../services/api/client';
import { dashboardCache } from '../../../services/api/cache';
import type { ChatMessage, ChatSession, GenerationResponse, QueryOptions } from '../types';
import { handleStreamResponse, mapBackendCitations } from './stream';

export { deduplicateCitations, mapBackendCitations } from './stream';

export const chatApi = {
  submitQuery: (repositoryId: string, query: string, options?: QueryOptions, opts?: RequestInit) =>
    post<GenerationResponse>('/queries', { repository_id: repositoryId, query, options: options || {} }, opts),

  getSessions: async (repositoryId: string, opts?: RequestInit): Promise<ChatSession[]> => {
    try {
      const sessions = await get<ChatSession[]>(`/chat/sessions?repository_id=${encodeURIComponent(repositoryId)}`, opts);
      if (sessions && sessions.length > 0) return sessions;
    } catch { /* fallback */ }
    const cached = dashboardCache.getSessionId(repositoryId);
    return cached ? [{ id: cached, repository_id: repositoryId, created_at: new Date().toISOString() }] : [];
  },

  createSession: async (repositoryId: string, opts?: RequestInit): Promise<ChatSession> => {
    try {
      const session = await post<ChatSession>('/chat/sessions', { repository_id: repositoryId }, opts);
      if (session) {
        dashboardCache.setSessionId(repositoryId, session.id);
        return session;
      }
    } catch { /* fallback */ }
    const fallbackId = `session-${Date.now()}`;
    dashboardCache.setSessionId(repositoryId, fallbackId);
    return { id: fallbackId, repository_id: repositoryId, created_at: new Date().toISOString() };
  },

  getMessages: async (sessionId: string, opts?: RequestInit): Promise<ChatMessage[]> => {
    try {
      const messages = await get<ChatMessage[]>(`/chat/sessions/${encodeURIComponent(sessionId)}/messages`, opts);
      return messages.map((m) => ({ ...m, citations: mapBackendCitations(m.citations) }));
    } catch {
      return [];
    }
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repository_id: repositoryId, content, session_id: activeSessionId }),
        signal,
      });
      if (!res.ok) throw new ApiError(res.status, `Request failed with status ${res.status}`);
      return await handleStreamResponse(res, onToken);
    } catch (streamErr) {
      if (signal?.aborted) throw streamErr;
      const resp = await chatApi.submitQuery(repositoryId, content, undefined, { signal });
      if (resp.answer) onToken(resp.answer);
      return {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: resp.answer,
        citations: mapBackendCitations(resp.citations),
        created_at: new Date().toISOString(),
      };
    }
  },

  deleteSessions: async (repositoryId: string, opts?: RequestInit): Promise<void> => {
    dashboardCache.clear(repositoryId);
    try {
      await del<void>(`/chat/sessions?repository_id=${encodeURIComponent(repositoryId)}`, opts);
    } catch { /* ignore */ }
  },
};
