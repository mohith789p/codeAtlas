import { useEffect, useState } from 'react';
import { chatApi } from '../api/chat';
import type { ChatMessage } from '../types';
import { repositoriesApi } from '../../repositories/api/repositories';
import type { Repository } from '../../repositories/types';
import { dashboardCache } from '../../../services/api/cache';

export function useChatInit(repoId: string | undefined, initialRepo: Repository | null) {
  const [repository, setRepository] = useState<Repository | null>(() => initialRepo);
  const [sessionId, setSessionId] = useState<string | null>(() => (repoId ? dashboardCache.getSessionId(repoId) : null));
  const [messages, setMessages] = useState<ChatMessage[]>(() => (repoId ? dashboardCache.getMessages(repoId) ?? [] : []));
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    if (initialRepo) {
      setRepository(initialRepo);
      if (repoId) dashboardCache.setRepository(repoId, initialRepo);
    }
  }, [initialRepo, repoId]);

  useEffect(() => {
    if (!repoId || (dashboardCache.getSessionId(repoId) && dashboardCache.getMessages(repoId))) return;
    const controller = new AbortController();

    const startSession = () => {
      chatApi.getSessions(repoId, { signal: controller.signal })
        .then((sessions) => {
          if (sessions.length > 0) {
            const s = sessions[sessions.length - 1];
            setSessionId(s.id);
            dashboardCache.setSessionId(repoId, s.id);
            return chatApi.getMessages(s.id, { signal: controller.signal });
          }
          return chatApi.createSession(repoId, { signal: controller.signal }).then((s) => {
            setSessionId(s.id);
            dashboardCache.setSessionId(repoId, s.id);
            return [] as ChatMessage[];
          });
        })
        .then((msgs) => {
          if (msgs) {
            setMessages(msgs);
            dashboardCache.setMessages(repoId, msgs);
          }
        })
        .catch((err) => {
          if (err?.name === 'AbortError') return;
          setInitError('Could not initialize chat session.');
        });
    };

    const cur = repository || (repoId ? dashboardCache.getRepository(repoId) : null);
    if (cur?.status === 'ready') {
      startSession();
      return () => controller.abort();
    }

    repositoriesApi.monitorUntilReady(repoId, {
      signal: controller.signal,
      onStatus: (data) => {
        setRepository(data);
        dashboardCache.setRepository(repoId, data);
      },
    }).then(() => startSession()).catch(() => undefined);

    return () => controller.abort();
  }, [repoId, repository]);

  return { repository, sessionId, messages, setMessages, initError };
}
