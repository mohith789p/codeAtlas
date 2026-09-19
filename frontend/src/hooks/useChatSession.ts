import { useState, useEffect, useCallback } from 'react';
import { chatApi, type ChatMessage } from '../api/chat';
import { repositoriesApi, type Repository } from '../api/repositories';
import { dashboardCache } from '../api/cache';
import { ApiError } from '../api/client';

export function useChatSession(repoId: string | undefined, initialRepo: Repository | null) {
  const [repository, setRepository] = useState<Repository | null>(() => initialRepo);
  const [sessionId, setSessionId] = useState<string | null>(() => (repoId ? dashboardCache.getSessionId(repoId) : null));
  const [messages, setMessages] = useState<ChatMessage[]>(() => (repoId ? dashboardCache.getMessages(repoId) ?? [] : []));
  const [sending, setSending] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  // Sync initialRepo
  useEffect(() => {
    if (initialRepo) {
      setRepository(initialRepo);
      if (repoId) dashboardCache.setRepository(repoId, initialRepo);
    }
  }, [initialRepo, repoId]);

  // Initialise session on mount or readiness change
  useEffect(() => {
    if (!repoId) return;
    if (dashboardCache.getSessionId(repoId) && dashboardCache.getMessages(repoId)) {
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    const initChat = () => {
      chatApi
        .getSessions(repoId, { signal: controller.signal })
        .then((sessions) => {
          if (cancelled) return;
          if (sessions.length > 0) {
            const session = sessions[sessions.length - 1];
            setSessionId(session.id);
            dashboardCache.setSessionId(repoId, session.id);
            return chatApi.getMessages(session.id, { signal: controller.signal });
          } else {
            return chatApi.createSession(repoId, { signal: controller.signal }).then((s) => {
              setSessionId(s.id);
              dashboardCache.setSessionId(repoId, s.id);
              return [] as ChatMessage[];
            });
          }
        })
        .then((msgs) => {
          if (cancelled) return;
          if (msgs) {
            setMessages(msgs);
            dashboardCache.setMessages(repoId, msgs);
          }
        })
        .catch((err) => {
          if (cancelled || err?.name === 'AbortError') return;
          console.error('[useChatSession] Failed to initialize chat session:', err);
          setInitError(
            err instanceof ApiError || err instanceof Error
              ? err.message
              : 'Could not connect to chat service.',
          );
        });
    };

    const currentRepo = repository || (repoId ? dashboardCache.getRepository(repoId) : null);
    if (currentRepo && currentRepo.status === 'ready') {
      initChat();
      return () => {
        cancelled = true;
        controller.abort();
      };
    }

    repositoriesApi
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: (data) => {
          setRepository(data);
          dashboardCache.setRepository(repoId, data);
        },
      })
      .then(() => {
        if (!cancelled) initChat();
      })
      .catch((err) => {
        if (cancelled || err?.name === 'AbortError') return;
        console.error('[useChatSession] Failed to monitor repository readiness:', err);
        setInitError(
          err instanceof ApiError || err instanceof Error
            ? err.message
            : 'Could not connect to chat service.',
        );
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [repoId, repository]);

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || !sessionId || sending) return;

      const userMsg: ChatMessage = {
        id: `local-${Date.now()}`,
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      };

      const streamMsgId = `stream-${Date.now()}`;
      const initialAssistantMsg: ChatMessage = {
        id: streamMsgId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => {
        const updated = [...prev, userMsg, initialAssistantMsg];
        if (repoId) dashboardCache.setMessages(repoId, updated);
        return updated;
      });
      setSending(true);

      try {
        const response = await chatApi.streamMessage(
          sessionId,
          text,
          (token: string) => {
            setMessages((prev) => {
              const updated = prev.map((m) =>
                m.id === streamMsgId ? { ...m, content: m.content + token } : m,
              );
              if (repoId) dashboardCache.setMessages(repoId, updated);
              return updated;
            });
          },
        );

        setMessages((prev) => {
          const updated = prev.map((m) => (m.id === streamMsgId ? response : m));
          if (repoId) dashboardCache.setMessages(repoId, updated);
          return updated;
        });
      } catch (err) {
        console.error('[useChatSession] Failed to send chat message:', err);
        const errMsg = err instanceof ApiError ? err.message : 'Failed to send message.';
        const errResponse: ChatMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${errMsg}`,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => {
          const withoutPlaceholder = prev.filter((m) => m.id !== streamMsgId);
          const updated = [...withoutPlaceholder, errResponse];
          if (repoId) dashboardCache.setMessages(repoId, updated);
          return updated;
        });
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending, repoId],
  );

  return {
    repository,
    sessionId,
    messages,
    sending,
    initError,
    sendMessage,
  };
}
