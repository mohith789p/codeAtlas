import React from 'react';
import { Sparkles } from 'lucide-react';

interface ChatSuggestionsProps {
  onSelect: (q: string) => void;
}

const QUESTIONS = [
  'How does authentication work in this repository?',
  'Where is the main entry point of the application?',
  'How do the core modules interact with each other?',
  'Where is error handling implemented?',
];

export const ChatSuggestions: React.FC<ChatSuggestionsProps> = ({ onSelect }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', margin: 'auto 0' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-violet-soft)' }}>
      <Sparkles size={16} />
      <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Explore with AI</span>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px', width: '100%', maxWidth: '640px' }}>
      {QUESTIONS.map((q) => (
        <button
          key={q}
          type="button"
          onClick={() => onSelect(q)}
          style={{
            textAlign: 'left',
            padding: '10px 14px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-card)',
            color: 'var(--text-secondary)',
            fontSize: 'var(--text-meta)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-hover)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          {q}
        </button>
      ))}
    </div>
  </div>
);
