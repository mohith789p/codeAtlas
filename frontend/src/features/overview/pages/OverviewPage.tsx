import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { repositoriesApi } from '../../repositories/api/repositories';
import type { Repository } from '../../repositories/types';
import { chatApi } from '../../chat/api/chat';
import { dashboardCache } from '../../../services/api/cache';
import type { DashboardContextType } from '../../../shared/components/layout/DashboardShell';
import { Spinner, ErrorState } from '../../../shared/components/ui/States';
import { OverviewHeader } from '../components/OverviewHeader';
import { MetricsRibbon } from '../components/MetricsRibbon';
import { LanguageBreakdown } from '../components/LanguageBreakdown';
import { PipelineTracker } from '../components/PipelineTracker';
import { RepoDetailsGrid } from '../components/RepoDetailsGrid';
import './OverviewPage.css';

export const OverviewPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const outletContext = useOutletContext<DashboardContextType | null>();

  const cached = repoId ? dashboardCache.getRepository(repoId) : null;
  const initial = outletContext?.repository || cached;
  const [repo, setRepo] = useState<Repository | null>(initial);
  const [loading, setLoading] = useState(!initial);
  const [errorMsg, setErrorMsg] = useState('');
  const [unlinking, setUnlinking] = useState(false);

  const handleUnlink = async () => {
    if (!repoId || unlinking) return;
    setUnlinking(true);
    try {
      await chatApi.deleteSessions(repoId);
    } finally {
      dashboardCache.clear(repoId);
      navigate('/', { replace: true });
    }
  };

  useEffect(() => {
    if (!repoId) return;
    const controller = new AbortController();

    repositoriesApi
      .get(repoId, { signal: controller.signal })
      .then((data) => {
        setRepo(data);
        dashboardCache.setRepository(repoId, data);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        setErrorMsg('Failed to load repository overview.');
        setLoading(false);
      });

    return () => controller.abort();
  }, [repoId]);

  if (loading) {
    return (
      <div className="overview-loading-container">
        <Spinner size={28} label="Loading repository details..." />
        <p className="overview-loading-title">Retrieving Repository Overview...</p>
      </div>
    );
  }

  if (errorMsg || !repo) {
    return (
      <div className="overview">
        <ErrorState
          title="Could not load repository"
          message={errorMsg || 'Repository data is unavailable.'}
          action={
            <button
              type="button"
              className="btn-ghost-danger"
              onClick={() => window.location.reload()}
            >
              Retry
            </button>
          }
        />
      </div>
    );
  }

  return (
    <div className="overview">
      <OverviewHeader repo={repo} onUnlink={handleUnlink} unlinking={unlinking} />
      <div className="overview-grid-layout">
        <MetricsRibbon repo={repo} />
        <PipelineTracker repo={repo} />
        <LanguageBreakdown repo={repo} />
        <RepoDetailsGrid repo={repo} />
      </div>
    </div>
  );
};
