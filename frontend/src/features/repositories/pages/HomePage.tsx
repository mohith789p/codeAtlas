import React, { useState, useEffect, useId, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { Spinner } from '../../../shared/components/ui/States';
import { repositoriesApi } from '../api/repositories';
import { ApiError } from '../../../services/api/client';
import { IngestForm } from '../components/IngestForm';
import { TabMode } from '../components/TabSwitcher';
import { RecentRepos } from '../components/RecentRepos';
import './HomePage.css';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const panelId = useId();
  const firstFieldRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<TabMode>('url');
  const [urlFields, setUrlFields] = useState({ url: '', branch: '' });
  const [manualFields, setManualFields] = useState({ username: '', name: '', branch: '' });
  const [urlTouched, setUrlTouched] = useState<{ url?: boolean; branch?: boolean }>({});
  const [manualTouched, setManualTouched] = useState<{ username?: boolean; name?: boolean; branch?: boolean }>({});
  const [pageState, setPageState] = useState<'form' | 'loading' | 'error'>('form');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const url = searchParams.get('url');
    const branch = searchParams.get('branch') || '';
    const user = searchParams.get('username') || searchParams.get('owner');
    const name = searchParams.get('name') || searchParams.get('repo');
    if (url) {
      setUrlFields({ url, branch });
      setMode('url');
    } else if (user || name) {
      setManualFields({ username: user || '', name: name || '', branch });
      setMode('manual');
    }
  }, [searchParams]);

  const urlErrors = !urlFields.url.trim()
    ? { url: 'Repository URL is required.' }
    : !/^https?:\/\/.+/.test(urlFields.url.trim())
    ? { url: 'Please enter a valid URL starting with https://' }
    : {};
  const manualErrors = {
    ...(!manualFields.username.trim() ? { username: 'Username is required.' } : {}),
    ...(!manualFields.name.trim() ? { name: 'Repository name is required.' } : {}),
  };
  const isValid = mode === 'url' ? Object.keys(urlErrors).length === 0 : Object.keys(manualErrors).length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'url') setUrlTouched({ url: true });
    else setManualTouched({ username: true, name: true });
    if (!isValid) return;

    setPageState('loading');
    setErrorMsg('');
    const payload = mode === 'url'
      ? { mode: 'url' as const, url: urlFields.url.trim(), ...(urlFields.branch.trim() ? { branch: urlFields.branch.trim() } : {}) }
      : { mode: 'manual' as const, username: manualFields.username.trim(), name: manualFields.name.trim(), ...(manualFields.branch.trim() ? { branch: manualFields.branch.trim() } : {}) };

    try {
      const repo = await repositoriesApi.ingest(payload);
      try {
        const stored = JSON.parse(localStorage.getItem('codeatlas:recent_repos') || '[]');
        const updated = [{ id: repo.id, name: repo.name, owner: repo.owner, branch: repo.branch }, ...stored.filter((r: any) => r.id !== repo.id)].slice(0, 5);
        localStorage.setItem('codeatlas:recent_repos', JSON.stringify(updated));
      } catch { /* ignore */ }
      navigate(`/dashboard/${repo.id}/overview`);
    } catch (err: any) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to link repository. Please verify details.');
      setPageState('error');
    }
  };

  if (pageState === 'loading') {
    return (
      <main className="home" id="main-content">
        <div className="home-card">
          <div className="home-loading" role="status">
            <Spinner size={28} label="Linking repository…" />
            <p className="home-loading-label">Connecting Repository…</p>
            <p className="home-loading-sublabel">Parsing structure, branches, and dependencies.</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="home" id="main-content">
      <div className="home-brand">
        <img src="/favicon.svg" alt="CodeAtlas" className="home-brand-logo" />
        <span className="home-brand-name">CodeAtlas</span>
      </div>
      <div className="home-headline-block">
        <h1 className="home-headline">Codebase <span className="home-headline-accent">Intelligence</span></h1>
        <p className="home-supporting">Analyze architecture, inspect file trees, and interrogate dependencies.</p>
      </div>

      <IngestForm
        id={panelId}
        mode={mode}
        onModeChange={(m) => { setMode(m); setPageState('form'); setErrorMsg(''); setTimeout(() => firstFieldRef.current?.focus(), 50); }}
        urlFields={urlFields} setUrlFields={setUrlFields}
        manualFields={manualFields} setManualFields={setManualFields}
        onSubmit={handleSubmit} firstFieldRef={firstFieldRef}
        urlTouched={urlTouched} setUrlTouched={setUrlTouched}
        manualTouched={manualTouched} setManualTouched={setManualTouched}
        urlErrors={urlErrors} manualErrors={manualErrors} errorMsg={errorMsg}
      />

      <RecentRepos onSelect={(r) => navigate(`/dashboard/${r.id}/overview`)} />

      <div className="home-reassurance">
        <ShieldCheck size={13} />
        <span>Read-only indexing &bull; No credentials stored &bull; Local analysis</span>
      </div>
    </main>
  );
};
