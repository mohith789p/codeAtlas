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
