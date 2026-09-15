import React, { useState, useEffect, useId, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Link2, User, AlertCircle, ShieldCheck } from 'lucide-react';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/States';
import { repositoriesApi, type IngestPayload } from '../api/repositories';
import { ApiError } from '../api/client';
import './HomePage.css';

// ─── Types ───────────────────────────────────────────────────────────────────

type TabMode = 'url' | 'manual';

interface UrlFields { url: string; branch: string }
interface ManualFields { username: string; name: string; branch: string }

interface UrlErrors { url?: string }
interface ManualErrors { username?: string; name?: string }

// ─── Validation ──────────────────────────────────────────────────────────────

function validateUrl(f: UrlFields): UrlErrors {
  const errors: UrlErrors = {};
  if (!f.url.trim()) {
    errors.url = 'Repository URL is required.';
  } else if (!/^https?:\/\/.+/.test(f.url.trim())) {
    errors.url = 'Please enter a valid URL starting with https://';
  }
  return errors;
}

function validateManual(f: ManualFields): ManualErrors {
  const errors: ManualErrors = {};
  if (!f.username.trim()) errors.username = 'username is required.';
  if (!f.name.trim()) errors.name = 'Repository name is required.';
  return errors;
}

// ─── Tab Switcher ─────────────────────────────────────────────────────────────

interface TabSwitcherProps {
  mode: TabMode;
  onChange: (mode: TabMode) => void;
}

const TabSwitcher: React.FC<TabSwitcherProps> = ({ mode, onChange }) => {
  const id = useId();

  return (
    <div
      className="tab-switcher"
      role="tablist"
      aria-label="Input method"
    >
      <button
        id={`${id}-tab-url`}
        role="tab"
        aria-selected={mode === 'url'}
        aria-controls={`${id}-panel`}
        className={['tab-btn', mode === 'url' ? 'tab-btn-active' : ''].filter(Boolean).join(' ')}
        onClick={() => onChange('url')}
        type="button"
      >
        <span className="tab-btn-icon" aria-hidden="true">
          <Link2 size={14} strokeWidth={2} />
        </span>
        URL
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
        <span className="tab-btn-icon" aria-hidden="true">
          <User size={14} strokeWidth={2} />
        </span>
        Username
      </button>
    </div>
  );
};

// ─── Home Page ────────────────────────────────────────────────────────────────

type PageState = 'form' | 'loading' | 'error';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const panelId = useId();

  // ── Tab mode
  const [mode, setMode] = useState<TabMode>('url');

  // ── Form values
  const [urlFields, setUrlFields] = useState<UrlFields>({ url: '', branch: '' });
  const [manualFields, setManualFields] = useState<ManualFields>({ username: '', name: '', branch: '' });

  // Pre-fill from query parameters (refactored from IngestionPage)
  useEffect(() => {
    const urlParam = searchParams.get('url');
    const branchParam = searchParams.get('branch');
    const usernameParam = searchParams.get('username') || searchParams.get('owner');
    const nameParam = searchParams.get('name') || searchParams.get('repo');
    const modeParam = searchParams.get('mode');

    if (urlParam) {
      setUrlFields({ url: urlParam, branch: branchParam || '' });
      setMode('url');
    } else if (usernameParam || nameParam) {
      setManualFields({
        username: usernameParam || '',
        name: nameParam || '',
        branch: branchParam || '',
      });
      setMode('manual');
    } else if (modeParam === 'manual') {
      setMode('manual');
    }
  }, [searchParams]);

  // ── Touched tracking (reset on tab switch)
  const [urlTouched, setUrlTouched] = useState<Partial<Record<keyof UrlFields, boolean>>>({});
  const [manualTouched, setManualTouched] = useState<Partial<Record<keyof ManualFields, boolean>>>({});

  // ── Page state
  const [pageState, setPageState] = useState<PageState>('form');
  const [errorMsg, setErrorMsg] = useState('');

  // ── First-field ref for focus-on-tab-switch
  const firstFieldRef = useRef<HTMLInputElement>(null);

  // Validation derived values
  const urlErrors = validateUrl(urlFields);
  const manualErrors = validateManual(manualFields);
  const isValid = mode === 'url'
    ? Object.keys(urlErrors).length === 0
    : Object.keys(manualErrors).length === 0;

  // Auto-fill username from URL (quality-of-life, Tab 1 → Tab 2 handoff)
  useEffect(() => {
    if (!urlFields.url) return;
    try {
      const u = new URL(urlFields.url);
      const segs = u.pathname.replace(/^\//, '').split('/');
      if (segs.length >= 2) {
        setManualFields(prev => ({
          ...prev,
          username: prev.username || segs[0],
          name: prev.name || segs[1].replace(/\.git$/, ''),
        }));
      }
    } catch { /* not a full URL yet */ }
  }, [urlFields.url]);

  // Reset error + focus first field when switching tabs
  const handleModeChange = (next: TabMode) => {
    setMode(next);
    setPageState('form');
    setErrorMsg('');
    setTimeout(() => firstFieldRef.current?.focus(), 50);
  };

  // ── Field change helpers
  const setUrl = (field: keyof UrlFields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setUrlFields(v => ({ ...v, [field]: e.target.value }));
  const setManual = (field: keyof ManualFields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setManualFields(v => ({ ...v, [field]: e.target.value }));

  const blurUrl = (field: keyof UrlFields) => () => setUrlTouched(t => ({ ...t, [field]: true }));
  const blurManual = (field: keyof ManualFields) => () => setManualTouched(t => ({ ...t, [field]: true }));

  // ── Submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Show all errors
    if (mode === 'url') {
      setUrlTouched({ url: true, branch: true });
    } else {
      setManualTouched({ username: true, name: true, branch: true });
    }
    if (!isValid) return;

    setPageState('loading');
    setErrorMsg('');

    const payload: IngestPayload = mode === 'url'
      ? {
        mode: 'url',
        url: urlFields.url.trim(),
        ...(urlFields.branch.trim() ? { branch: urlFields.branch.trim() } : {}),
      }
      : {
        mode: 'manual',
        username: manualFields.username.trim(),
        name: manualFields.name.trim(),
        ...(manualFields.branch.trim() ? { branch: manualFields.branch.trim() } : {}),
      };

    try {
      const repo = await repositoriesApi.ingest(payload);
      navigate(`/dashboard/${repo.id}/overview`);
    } catch (err) {
      const msg = err instanceof ApiError
        ? err.message
        : 'Failed to connect repository. Please check your details and try again.';
      setErrorMsg(msg);
      setPageState('error');
    }
  };

  // ── Loading state (replaces card body)
  if (pageState === 'loading') {
    return (
      <main className="home" id="main-content">
        <div className="home-brand" aria-hidden="true">
          <img src="/favicon.svg" alt="CodeAtlas logo" className="home-brand-logo" />
          <span className="home-brand-name">CodeAtlas</span>
        </div>

        <div className="home-card">
          <div className="home-loading" role="status" aria-live="polite">
            <Spinner size={32} label="Connecting repository…" />
            <p className="home-loading-label">Connecting repository…</p>
            <p className="home-loading-sublabel">
              This may take a moment while CodeAtlas processes your repository.
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="home" id="main-content">
      {/* Brand */}
      <div className="home-brand" aria-hidden="true">
        <img src="/favicon.svg" alt="CodeAtlas logo" className="home-brand-logo" />
        <span className="home-brand-name">CodeAtlas</span>
      </div>

      {/* Headline */}
      <div className="home-headline-block">
        <h1 className="home-headline">
          Understand your <span className="home-headline-gradient">codebase.</span>
        </h1>
        <p className="home-supporting">
          Explore files, discover architecture, and ask questions
        </p>
      </div>

      {/* Connection card */}
      <div className="home-card">
        {/* Tab switcher */}
        <TabSwitcher mode={mode} onChange={handleModeChange} />

        {/* Form */}
        <form
          id={panelId}
          role="tabpanel"
          className="home-form"
          onSubmit={handleSubmit}
          noValidate
          aria-label={
            mode === 'url'
              ? 'Connect by repository URL'
              : 'Connect by repository name'
          }
        >
          {/* Tab 1 — Repository URL */}
          {mode === 'url' && (
            <div className="home-form-fields" key="url-fields">
              <Input
                ref={firstFieldRef}
                label="Repository URL"
                id="home-url"
                type="url"
                placeholder="https://github.com/username/reponame"
                value={urlFields.url}
                onChange={setUrl('url')}
                onBlur={blurUrl('url')}
                error={urlTouched.url ? urlErrors.url : undefined}
                autoComplete="url"
                autoFocus
              />
              <Input
                label="Branch"
                id="home-url-branch"
                type="text"
                placeholder="e.g. main"
                value={urlFields.branch}
                onChange={setUrl('branch')}
                optional
              />
            </div>
          )}

          {/* Tab 2 — Repository */}
          {mode === 'manual' && (
            <div className="home-form-fields" key="manual-fields">
              <div className="home-form-grid">
                <Input
                  ref={firstFieldRef}
                  label="Username "
                  id="home-username"
                  type="text"
                  placeholder="e.g. manidweep1306"
                  value={manualFields.username}
                  onChange={setManual('username')}
                  onBlur={blurManual('username')}
                  error={manualTouched.username ? manualErrors.username : undefined}
                  autoComplete="username"
                  autoFocus
                />
                <Input
                  label="Repository"
                  id="home-repo-name"
                  type="text"
                  placeholder="e.g. TalkToDB"
                  value={manualFields.name}
                  onChange={setManual('name')}
                  onBlur={blurManual('name')}
                  error={manualTouched.name ? manualErrors.name : undefined}
                />
              </div>
              <Input
                label="Branch"
                id="home-manual-branch"
                type="text"
                placeholder="e.g. main"
                value={manualFields.branch}
                onChange={setManual('branch')}
                optional
              />
            </div>
          )}

          {/* Error banner */}
          {pageState === 'error' && errorMsg && (
            <div className="home-form-error" role="alert">
              <AlertCircle size={14} aria-hidden="true" style={{ flexShrink: 0 }} />
              {errorMsg}
            </div>
          )}

          {/* Submit */}
          <div className="home-form-actions">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              id="home-connect-submit"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Connect repository
            </Button>
          </div>
        </form>
      </div>

      {/* Reassurance — low visual weight */}
      <div className="home-reassurance">
        <ShieldCheck size={14} className="home-reassurance-icon" aria-hidden="true" />
        <span>CodeAtlas reads repository structure &bull; No credentials stored &bull; Read-only</span>
      </div>
    </main>
  );
};
