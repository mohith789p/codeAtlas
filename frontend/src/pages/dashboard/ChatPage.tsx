import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useParams, useNavigate } from 'react-router-dom';
import { Bot, Send, MessageSquare, ArrowRight, FileCode } from 'lucide-react';
import { chatApi, type ChatMessage, type Citation } from '../../api/chat';
import { repositoriesApi, type Repository } from '../../api/repositories';
import { ApiError } from '../../api/client';
import { Spinner } from '../../components/ui/States';
import './ChatPage.css';

// ─── Example questions (teaching capability on empty state) ──────────────────

const EXAMPLE_QUESTIONS = [
  'How does authentication work in this repository?',
  'Where is the main entry point of the application?',
  'How do the core modules interact with each other?',
  'Where is error handling implemented?',
];

function stripCitationMetadata(content: string, citations: Citation[]): string {
  if (!citations.length) return content;

  const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  const citationPatterns = citations.flatMap((citation) => {
    if (!citation.file || citation.line_start === undefined) return [];
    const file = escapeRegex(citation.file);
    const basename = file.split('/').pop() ?? file;
    const end = citation.line_end ?? citation.line_start;
    const range = citation.line_start === end
      ? `${citation.line_start}`
      : `${citation.line_start}[-–]${end}`;
    const symbol = citation.symbol
      ? `(?:[ \\t]+(?:\\(${escapeRegex(citation.symbol)}\\)|${escapeRegex(citation.symbol)}))?`
      : `(?:[ \\t]+\\([A-Za-z_][A-Za-z0-9_.]*\\))?`;
    return [`[ \\t]*\\x60?(?:${file}|${basename}):${range}${symbol}[ \\t]*\\x60?`];
  });

  if (!citationPatterns.length) return content;
  const pattern = new RegExp(citationPatterns.join('|'), 'g');
  return content
    .split(/(```[\s\S]*?```)/g)
    .map((part, index) => index % 2 === 1 ? part : part.replace(pattern, ''))
    .join('')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// ─── Citation chip ────────────────────────────────────────────────────────────

interface CitationChipProps {
  citation: Citation;
  onNavigate: (citation: Citation) => void;
}

const CitationChip: React.FC<CitationChipProps> = ({ citation, onNavigate }) => {
  const fileName = citation.file.split('/').pop() ?? citation.file;
  const lineRange =
    citation.line_start
      ? citation.line_end && citation.line_end !== citation.line_start
        ? `:${citation.line_start}–${citation.line_end}`
        : `:${citation.line_start}`
      : '';

  return (
    <button
      className="citation-chip"
      onClick={() => onNavigate(citation)}
      aria-label={`Navigate to ${citation.file}${lineRange}`}
      title={`${citation.file}${lineRange}`}
    >
      <FileCode size={12} aria-hidden="true" />
      <span className="citation-chip-file">{fileName}</span>
      {lineRange && (
        <span className="citation-chip-lines">{lineRange}</span>
      )}
    </button>
  );
};

// ─── Message bubble ───────────────────────────────────────────────────────────

interface MessageProps {
  message: ChatMessage;
  onCitationNavigate: (citation: Citation) => void;
}

const MessageBubble: React.FC<MessageProps> = ({ message, onCitationNavigate }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div
        className="message-row message-row-user"
        aria-label={`You: ${message.content}`}
      >
        <div className="message-bubble-user" role="article">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div
      className="message-row message-row-assistant"
      aria-label={`CodeAtlas: ${message.content}`}
    >
      {/* AI identity marker — violet icon + label */}
      <div className="message-identity">
        <span className="message-identity-icon" aria-hidden="true">
          <Bot size={14} />
        </span>
        <span className="message-identity-label">CodeAtlas Bot</span>
      </div>

      {/* Response body — neutral text, NOT violet */}
      <div className="message-bubble-assistant" role="article">
        <div className="message-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {stripCitationMetadata(message.content, message.citations ?? [])}
        </ReactMarkdown>
        </div>
      </div>

      {/* Citations block — below response */}
      {message.citations && message.citations.length > 0 && (
        <div className="citations-block" aria-label="Source references">
          <p className="citations-label">Sources</p>
          <div className="citation-list">
            {message.citations.map((citation, i) => (
              <CitationChip
                key={`${citation.file}-${i}`}
                citation={citation}
                onNavigate={onCitationNavigate}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Typing indicator ─────────────────────────────────────────────────────────

const TypingIndicator: React.FC = () => (
  <div className="message-row message-row-assistant">
    <div className="message-identity">
      <span className="message-identity-icon" aria-hidden="true">
        <Bot size={14} />
      </span>
      <span className="message-identity-label">CodeAtlas</span>
    </div>
    <div className="message-loading" role="status" aria-label="CodeAtlas is thinking…">
      <div className="typing-dots" aria-hidden="true">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
      <span style={{ fontSize: 'var(--text-meta)', color: 'var(--text-muted)' }}>
        Thinking…
      </span>
    </div>
  </div>
);

// ─── Chat Page ────────────────────────────────────────────────────────────────

export const ChatPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [repository, setRepository] = useState<Repository | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initialise session on mount
  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    const controller = new AbortController();

    repositoriesApi
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: setRepository,
      })
      .then(() => chatApi.getSessions(repoId, { signal: controller.signal }))
      .then((sessions) => {
        if (cancelled) return;
        if (sessions.length > 0) {
          const session = sessions[sessions.length - 1];
          setSessionId(session.id);
          return chatApi.getMessages(session.id, { signal: controller.signal });
        } else {
          return chatApi.createSession(repoId, { signal: controller.signal }).then((s) => {
            setSessionId(s.id);
            return [] as ChatMessage[];
          });
        }
      })
      .then((msgs) => {
        if (cancelled) return;
        if (msgs) setMessages(msgs);
      })
      .catch((err) => {
        if (cancelled || err?.name === 'AbortError') return;
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
  }, [repoId]);

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

    const userMsg: ChatMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);

    try {
      const response = await chatApi.sendMessage(sessionId, text);
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      const errMsg =
        err instanceof ApiError ? err.message : 'Failed to send message.';
      const errResponse: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${errMsg}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errResponse]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
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
        {/* Init error */}
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

        {/* Empty state — teach capability */}
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

        {/* Messages */}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onCitationNavigate={handleCitationNavigate}
          />
        ))}

        {/* AI typing indicator */}
        {sending && <TypingIndicator />}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} aria-hidden="true" />
      </div>

      {/* Chat input — fixed at bottom */}
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
