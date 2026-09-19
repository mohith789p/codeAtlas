import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import { Send, MessageSquare, ArrowRight } from 'lucide-react';
import type { Citation } from '../../api/chat';
import { dashboardCache } from '../../api/cache';
import type { DashboardContextType } from '../../components/layout/DashboardShell';
import { Spinner } from '../../components/ui/States';
import { MessageBubble } from './components/MessageBubble';
import { useChatSession } from '../../hooks/useChatSession';
import './ChatPage.css';

const EXAMPLE_QUESTIONS = [
  'How does authentication work in this repository?',
  'Where is the main entry point of the application?',
  'How do the core modules interact with each other?',
  'Where is error handling implemented?',
];

export const ChatPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const outletContext = useOutletContext<DashboardContextType | null>();
  const initialRepo = outletContext?.repository || (repoId ? dashboardCache.getRepository(repoId) : null);

  const { repository, sessionId, messages, sending, initError, sendMessage } = useChatSession(
    repoId,
    initialRepo,
  );

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // Navigate to Files page when a citation is clicked
  const handleCitationNavigate = useCallback(
    (citation: Citation) => {
      const params = new URLSearchParams({ path: citation.file });
      if (citation.line_start) {
        const end = citation.line_end ?? citation.line_start;
        params.set('lines', `${citation.line_start}-${end}`);
      }
      navigate(`/dashboard/${repoId}/files?${params.toString()}`);
    },
    [navigate, repoId],
  );

  const handleSend = async (content: string) => {
    const text = content.trim();
    if (!text || !sessionId || sending) return;
    setInput('');
    await sendMessage(text);
    inputRef.current?.focus();
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  const handleExampleQuestion = (q: string) => {
    setInput(q);
    inputRef.current?.focus();
  };

  const hasMessages = messages.length > 0;
  const canSend = input.trim().length > 0 && !sending && !!sessionId;
  const chatLocked = !repository || repository.status !== 'ready';

  return (
    <div className="chat-page">
      {/* Message history */}
      <div
        className="chat-messages"
        role="log"
        aria-live="polite"
        aria-label="Conversation"
      >
        {initError && (
          <div
            role="alert"
            style={{
              padding: 'var(--space-3) var(--space-4)',
              background: 'rgba(248,113,113,0.08)',
              border: '1px solid var(--border-error)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--error)',
              fontSize: 'var(--text-meta)',
              alignSelf: 'center',
              maxWidth: 480,
            }}
          >
            {initError}
          </div>
        )}

        {chatLocked && !initError && (
          <div className="chat-ingestion-lock" role="status">
            <Spinner size={20} label="Waiting for ingestion to complete" />
            <span>Chat unlocks when ingestion is complete. Current stage: {repository?.status ?? 'starting'}.</span>
          </div>
        )}

        {!hasMessages && !initError && !chatLocked && (
          <div className="chat-empty">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)' }}>
              <span style={{ color: 'var(--accent-violet-ui)', opacity: 0.7 }}>
                <MessageSquare size={32} />
              </span>
              <p className="chat-empty-heading">
                Ask anything about this repository. Every answer comes with source references.
              </p>
            </div>

            <div className="example-questions" role="list" aria-label="Example questions">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  className="example-question"
                  onClick={() => handleExampleQuestion(q)}
                  role="listitem"
                  aria-label={`Ask: ${q}`}
                >
                  <ArrowRight
                    size={13}
                    className="example-question-icon"
                    aria-hidden="true"
                  />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onCitationNavigate={handleCitationNavigate}
          />
        ))}

        <div ref={messagesEndRef} aria-hidden="true" />
      </div>

      {/* Chat input */}
      <div className="chat-input-area">
        <form
          className="chat-input-form"
          onSubmit={handleFormSubmit}
          aria-label="Send a message"
        >
          <textarea
            ref={inputRef}
            className="chat-input-field"
            placeholder="Ask about the codebase…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            aria-label="Message input"
            aria-multiline="true"
            disabled={!sessionId || !!initError}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!canSend}
            aria-label="Send message"
            title="Send (Enter)"
          >
            {sending ? (
              <Spinner size={16} label="Sending message" />
            ) : (
              <Send size={16} aria-hidden="true" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
