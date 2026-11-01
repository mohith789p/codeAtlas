import React, { useRef, useEffect } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';
import './ChatInputBar.css';

interface ChatInputBarProps {
  input: string;
  setInput: (val: string) => void;
  onSend: (text: string) => void;
  sending: boolean;
  disabled?: boolean;
}

export const ChatInputBar: React.FC<ChatInputBarProps> = ({
  input,
  setInput,
  onSend,
  sending,
  disabled,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!sending) textareaRef.current?.focus();
  }, [sending]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !sending && !disabled) {
        onSend(input);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !sending && !disabled) {
      onSend(input);
    }
  };

  return (
    <div className="chat-input-container">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={disabled ? 'Indexing repository...' : 'Ask anything about code, architecture, or dependencies...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || sending}
          rows={1}
        />
        <div className="chat-input-footer">
          <span className="chat-input-hint">Press Enter to send &bull; Shift+Enter for new line</span>
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || sending || disabled}
            aria-label="Send message"
          >
            {sending ? <Loader2 size={14} className="spin" /> : <ArrowUp size={15} strokeWidth={2.5} />}
          </button>
        </div>
      </form>
    </div>
  );
};
