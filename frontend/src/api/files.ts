/**
 * Files API
 *
 * Required endpoints (backend dependency):
 *
 * GET /api/repositories/:repoId/tree
 *   response: { tree: FileNode[] }
 *
 * GET /api/repositories/:repoId/files/*path
 *   response: { content: string, language: string }
 */

import { get } from './client';

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  size?: number;
}

export interface FileTreeResponse {
  tree: FileNode[];
}

export interface FileContentResponse {
  content: string;
  language: string;
  size?: number;
  encoding?: string;
}

export const filesApi = {
  getTree: (repoId: string, opts?: RequestInit) =>
    get<FileTreeResponse>(`/repositories/${repoId}/tree`, opts),

  getFile: (repoId: string, filePath: string) =>
    get<FileContentResponse>(
      `/repositories/${repoId}/files/${filePath
        .replace(/^\//, '')
        .split('/')
        .map(encodeURIComponent)
        .join('/')}`,
    ),
};
