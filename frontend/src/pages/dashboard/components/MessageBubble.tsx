import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot } from 'lucide-react';
import type { ChatMessage, Citation } from '../../../api/chat';
import { stripCitationMetadata } from '../../../utils/citations';
import { CitationChip } from './CitationChip';

interface MessageBubbleProps {
  message: ChatMessage;
  onCitationNavigate: (citation: Citation) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onCitationNavigate }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row message-row-user" aria-label={`You: ${message.content}`}>
        <div className="message-bubble-user" role="article">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div
      className="message-row message-row-assistant"
      aria-label={`CodeAtlas: ${message.content || 'Thinking…'}`}
    >
      <div className="message-identity">
        <span className="message-identity-icon" aria-hidden="true">
          <Bot size={14} />
        </span>
        <span className="message-identity-label">CodeAtlas Bot</span>
      </div>

      <div className="message-bubble-assistant" role="article">
        <div className="message-markdown">
          {message.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {stripCitationMetadata(message.content, message.citations ?? [])}
            </ReactMarkdown>
          ) : (
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
          )}
        </div>
      </div>

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
