import React from 'react';
import { Link2, User } from 'lucide-react';

export type TabMode = 'url' | 'manual';

interface TabSwitcherProps {
  id: string;
  mode: TabMode;
  onChange: (mode: TabMode) => void;
}

export const TabSwitcher: React.FC<TabSwitcherProps> = ({ id, mode, onChange }) => (
  <div className="tab-switcher" role="tablist" aria-label="Input method">
    <button
      id={`${id}-tab-url`}
      role="tab"
      aria-selected={mode === 'url'}
      aria-controls={`${id}-panel`}
      className={['tab-btn', mode === 'url' ? 'tab-btn-active' : ''].filter(Boolean).join(' ')}
      onClick={() => onChange('url')}
      type="button"
    >
      <span className="tab-btn-icon" aria-hidden="true"><Link2 size={13} strokeWidth={2} /></span>
      <span>Repository URL</span>
    </button>
    <button
      id={`${id}-tab-manual`}
      role="tab"
      aria-selected={mode === 'manual'}
      aria-controls={`${id}-panel`}
      className={['tab-btn', mode === 'manual' ? 'tab-btn-active' : ''].filter(Boolean).join(' ')}
      onClick={() => onChange('manual')}
      type="button"
    >
      <span className="tab-btn-icon" aria-hidden="true"><User size={13} strokeWidth={2} /></span>
      <span>Owner / Name</span>
    </button>
  </div>
);
