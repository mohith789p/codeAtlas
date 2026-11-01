import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useParams } from 'react-router-dom';
import { repositoriesApi } from '../../../features/repositories/api/repositories';
import type { Repository } from '../../../features/repositories/types';
import { chatApi } from '../../../features/chat/api/chat';
import { dashboardCache } from '../../../services/api/cache';
import { SidebarNav } from './SidebarNav';
import { WorkspaceHeader } from './WorkspaceHeader';
import './DashboardShell.css';

export interface DashboardContextType {
  repository: Repository | null;
  setRepository: React.Dispatch<React.SetStateAction<Repository | null>>;
}

export const DashboardShell: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [repository, setRepository] = useState<Repository | null>(() => (
    repoId ? dashboardCache.getRepository(repoId) : null
  ));
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
      .monitorUntilReady(repoId, {
        signal: controller.signal,
        onStatus: (data) => {
          setRepository(data);
          dashboardCache.setRepository(repoId, data);
        },
      })
      .then((readyRepo) => {
        setRepository(readyRepo);
        dashboardCache.setRepository(repoId, readyRepo);
      })
      .catch(() => undefined);

    return () => controller.abort();
  }, [repoId]);

  const base = `/dashboard/${repoId}`;

  return (
    <div className="shell">
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'sidebar-open' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <SidebarNav
        base={base}
        repository={repository}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        onUnlink={handleUnlink}
        unlinking={unlinking}
        onNavigate={() => setSidebarOpen(false)}
      />

      <div className="shell-content">
        <WorkspaceHeader
          repository={repository}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
        />
        <main id="main-content" style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet context={{ repository, setRepository } satisfies DashboardContextType} />
        </main>
      </div>
    </div>
  );
};
