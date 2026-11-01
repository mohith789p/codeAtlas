import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import type { Citation } from '../types';
import { dashboardCache } from '../../../services/api/cache';
import type { DashboardContextType } from '../../../shared/components/layout/DashboardShell';
import { MessageBubble } from '../components/MessageBubble';
import { ChatSuggestions } from '../components/ChatSuggestions';
import { ChatSplitViewer } from '../components/ChatSplitViewer';
import { ChatInputBar } from '../components/ChatInputBar';
import { useChatSession } from '../hooks/useChatSession';
import './ChatPage.css';

export const ChatPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const outletContext = useOutletContext<DashboardContextType | null>();
  const initialRepo = outletContext?.repository || (repoId ? dashboardCache.getRepository(repoId) : null);

  const { repository, sending, messages, initError, sendMessage } = useChatSession(repoId, initialRepo);
  const [input, setInput] = useState('');
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleOpenFull = (citation: Citation) => {
    const params = new URLSearchParams({ path: citation.file });
    if (citation.line_start) {
      params.set('lines', `${citation.line_start}-${citation.line_end ?? citation.line_start}`);
    }
    navigate(`/dashboard/${repoId}/files?${params.toString()}`);
  };

  const handleSend = async (text: string) => {
    setInput('');
    await sendMessage(text);
  };

  const isLocked = !repository || repository.status !== 'ready';

  return (
    <div className="chat-page">
      <div className="chat-main-column">
        <div className="chat-messages" role="log" aria-live="polite">
          {initError && (
            <div className="chat-alert-banner" role="alert">
              {initError}
            </div>
          )}

          {messages.length === 0 ? (
            <ChatSuggestions onSelect={handleSend} />
          ) : (
            messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                onCitationNavigate={(c) => setActiveCitation(c)}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <ChatInputBar
          input={input}
          setInput={setInput}
          onSend={handleSend}
          sending={sending}
          disabled={isLocked}
        />
      </div>

      {activeCitation && repoId && (
        <ChatSplitViewer
          repoId={repoId}
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
          onOpenFull={handleOpenFull}
        />
      )}
    </div>
  );
};
