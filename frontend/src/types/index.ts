export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Repository {
  id: number;
  name: string;
  status: 'processing' | 'ready' | 'error';
  file_count: number;
  chunk_count: number;
  created_at: string;
}

export interface FileNode {
  id?: number;
  name: string;
  path: string;
  type: 'file' | 'dir';
  size_bytes?: number;
  children?: FileNode[];
}

export interface FileDetail {
  id: number;
  path: string;
  extension: string;
  size_bytes: number;
  content: string;
}

export interface ChunkResult {
  id: number;
  file_path: string;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
}

export interface ChatSession {
  id: number;
  repo_id: number;
  title: string;
  created_at: string;
}

export interface SourceCitation {
  source_index: number;
  file_path: string;
  start_line: number;
  end_line: number;
  score: number;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  created_at: string;
}

export interface GeneratedDoc {
  id: number;
  repo_id: number;
  doc_type: 'readme' | 'architecture';
  content: string;
  created_at: string;
}
