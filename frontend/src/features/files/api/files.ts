import { get } from '../../../services/api/client';
import type { FileTreeResponse, FileContentResponse } from '../types';

export const filesApi = {
  getTree: async (repoId: string, opts?: RequestInit): Promise<FileTreeResponse> => {
    return get<FileTreeResponse>(`/repositories/${repoId}/tree`, opts);
  },

  getFile: async (repoId: string, filePath: string, opts?: RequestInit): Promise<FileContentResponse> => {
    const cleanPath = filePath
      .replace(/^\//, '')
      .split('/')
      .map(encodeURIComponent)
      .join('/');
    return get<FileContentResponse>(`/repositories/${repoId}/files/${cleanPath}`, opts);
  },
};
