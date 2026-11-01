import React from 'react';
import { AlertCircle } from 'lucide-react';
import { Input } from '../../../shared/components/ui/Input';
import { Button } from '../../../shared/components/ui/Button';
import { TabSwitcher, TabMode } from './TabSwitcher';
import './IngestForm.css';

interface IngestFormProps {
  id: string;
  mode: TabMode;
  onModeChange: (m: TabMode) => void;
  urlFields: { url: string; branch: string };
  setUrlFields: React.Dispatch<React.SetStateAction<{ url: string; branch: string }>>;
  manualFields: { username: string; name: string; branch: string };
  setManualFields: React.Dispatch<React.SetStateAction<{ username: string; name: string; branch: string }>>;
  onSubmit: (e: React.FormEvent) => void;
  firstFieldRef: React.RefObject<HTMLInputElement>;
  urlTouched: { url?: boolean; branch?: boolean };
  setUrlTouched: React.Dispatch<React.SetStateAction<{ url?: boolean; branch?: boolean }>>;
  manualTouched: { username?: boolean; name?: boolean; branch?: boolean };
  setManualTouched: React.Dispatch<React.SetStateAction<{ username?: boolean; name?: boolean; branch?: boolean }>>;
  urlErrors: { url?: string };
  manualErrors: { username?: string; name?: string };
  errorMsg: string;
}

export const IngestForm: React.FC<IngestFormProps> = ({
  id,
  mode,
  onModeChange,
  urlFields,
  setUrlFields,
  manualFields,
  setManualFields,
  onSubmit,
  firstFieldRef,
  urlTouched,
  setUrlTouched,
  manualTouched,
  setManualTouched,
  urlErrors,
  manualErrors,
  errorMsg,
}) => (
  <div className="home-card">
    <TabSwitcher id={id} mode={mode} onChange={onModeChange} />
    <form id={id} role="tabpanel" className="home-form" onSubmit={onSubmit} noValidate>
      {mode === 'url' ? (
        <div className="home-form-fields">
          <Input
            ref={firstFieldRef}
            label="Repository URL"
            id="home-url"
            type="url"
            placeholder="https://github.com/username/repository"
            value={urlFields.url}
            onChange={(e) => setUrlFields((v) => ({ ...v, url: e.target.value }))}
            onBlur={() => setUrlTouched((t) => ({ ...t, url: true }))}
            error={urlTouched.url ? urlErrors.url : undefined}
            autoFocus
          />
          <Input
            label="Branch"
            id="home-url-branch"
            type="text"
            placeholder="e.g. main"
            value={urlFields.branch}
            onChange={(e) => setUrlFields((v) => ({ ...v, branch: e.target.value }))}
            optional
          />
        </div>
      ) : (
        <div className="home-form-fields">
          <div className="home-form-grid">
            <Input
              ref={firstFieldRef}
              label="Username"
              id="home-username"
              type="text"
              placeholder="e.g. facebook"
              value={manualFields.username}
              onChange={(e) => setManualFields((v) => ({ ...v, username: e.target.value }))}
              onBlur={() => setManualTouched((t) => ({ ...t, username: true }))}
              error={manualTouched.username ? manualErrors.username : undefined}
              autoFocus
            />
            <Input
              label="Repository"
              id="home-repo-name"
              type="text"
              placeholder="e.g. react"
              value={manualFields.name}
              onChange={(e) => setManualFields((v) => ({ ...v, name: e.target.value }))}
              onBlur={() => setManualTouched((t) => ({ ...t, name: true }))}
              error={manualTouched.name ? manualErrors.name : undefined}
            />
          </div>
          <Input
            label="Branch"
            id="home-manual-branch"
            type="text"
            placeholder="e.g. main"
            value={manualFields.branch}
            onChange={(e) => setManualFields((v) => ({ ...v, branch: e.target.value }))}
            optional
          />
        </div>
      )}

      {errorMsg && (
        <div className="home-form-error" role="alert">
          <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="home-form-actions">
        <Button type="submit" variant="primary" size="lg" style={{ width: '100%', justifyContent: 'center' }}>
          Explore Repository
        </Button>
      </div>
    </form>
  </div>
);
