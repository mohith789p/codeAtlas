import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import api from '../api/client';
import { Repository } from '../types';
import { useAuth } from './AuthContext';

interface RepoContextType {
  repositories: Repository[];
  activeRepo: Repository | null;
  loading: boolean;
  setActiveRepo: (repo: Repository | null) => void;
  fetchRepositories: () => Promise<void>;
  deleteRepository: (repoId: number) => Promise<void>;
}

const RepoContext = createContext<RepoContextType | undefined>(undefined);

export const RepoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepo, setActiveRepoState] = useState<Repository | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRepositories = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await api.get<Repository[]>('/repositories');
      setRepositories(res.data);
      // Sync activeRepo with fresh data (e.g. status change from processing → ready)
      setActiveRepoState((prev) => {
        if (!prev) return res.data.length > 0 ? res.data[0] : null;
        const updated = res.data.find((r) => r.id === prev.id);
        return updated ?? (res.data.length > 0 ? res.data[0] : null);
      });
    } catch (err) {
      console.error('Failed to fetch repositories', err);
    } finally {
      setLoading(false);
    }
  };

  const setActiveRepo = (repo: Repository | null) => {
    setActiveRepoState(repo);
  };

  const deleteRepository = async (repoId: number) => {
    try {
      await api.delete(`/repositories/${repoId}`);
      const updated = repositories.filter((r) => r.id !== repoId);
      setRepositories(updated);
      setActiveRepoState((prev) => {
        if (prev?.id !== repoId) return prev;
        return updated.length > 0 ? updated[0] : null;
      });
    } catch (err) {
      console.error('Failed to delete repository', err);
      throw err;
    }
  };

  // Poll every 4 seconds while any repository is still in "processing" state
  useEffect(() => {
    const hasProcessing = repositories.some((r) => r.status === 'processing');
    if (hasProcessing && !pollingRef.current) {
      pollingRef.current = setInterval(() => {
        fetchRepositories();
      }, 4000);
    } else if (!hasProcessing && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [repositories]);

  useEffect(() => {
    if (user) {
      fetchRepositories();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return (
    <RepoContext.Provider
      value={{
        repositories,
        activeRepo,
        loading,
        setActiveRepo,
        fetchRepositories,
        deleteRepository,
      }}
    >
      {children}
    </RepoContext.Provider>
  );
};

export const useRepo = () => {
  const context = useContext(RepoContext);
  if (!context) {
    throw new Error('useRepo must be used within a RepoProvider');
  }
  return context;
};
