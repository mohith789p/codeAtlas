import { useState, useCallback } from 'react';
import { chatApi } from '../api/chat';
import type { ChatMessage } from '../types';
import type { Repository } from '../../repositories/types';
import { dashboardCache } from '../../../services/api/cache';
import { useChatInit } from './useChatInit';

export function useChatSession(repoId: string | undefined, initialRepo: Repository | null) {
  const { repository, sessionId, messages, setMessages, initError } = useChatInit(repoId, initialRepo);
  const [sending, setSending] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || (!sessionId && !repoId) || sending) return;

      const userMsg: ChatMessage = {
        id: `local-${Date.now()}`,
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      };
      const streamId = `stream-${Date.now()}`;
      const placeholder: ChatMessage = {
        id: streamId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => {
        const next = [...prev, userMsg, placeholder];
        if (repoId) dashboardCache.setMessages(repoId, next);
        return next;
      });
      setSending(true);

      try {
        const response = await chatApi.streamMessage(
          repoId || '',
          text,
          (token: string) => {
            setMessages((prev) => {
              const next = prev.map((m) => (m.id === streamId ? { ...m, content: m.content + token } : m));
              if (repoId) dashboardCache.setMessages(repoId, next);
              return next;
            });
          },
          undefined,
          sessionId,
        );
        setMessages((prev) => {
          const next = prev.map((m) => (m.id === streamId ? response : m));
          if (repoId) dashboardCache.setMessages(repoId, next);
          return next;
        });
      } catch (err: any) {
        const errMsg = err?.message || 'Failed to send message.';
        const errResponse: ChatMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${errMsg}`,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => {
          const next = [...prev.filter((m) => m.id !== streamId), errResponse];
          if (repoId) dashboardCache.setMessages(repoId, next);
          return next;
        });
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending, repoId, setMessages],
  );

  return { repository, sessionId, messages, sending, initError, sendMessage };
}
