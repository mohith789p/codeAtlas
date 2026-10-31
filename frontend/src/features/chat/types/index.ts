export interface BackendCitation {
  filepath: string;
  start_line: number;
  end_line: number;
  symbol?: string | null;
  confidence?: number;
  snippet?: string | null;
}

export interface GenerationResponse {
  answer: string;
  citations: BackendCitation[];
  provider: string;
  model: string;
  cache_hit?: boolean;
  latency_ms?: number;
  retrieved_chunks_count?: number;
}

export interface QueryOptions {
  top_k?: number;
  use_cache?: boolean;
  similarity_threshold?: number;
  dense_weight?: number;
  sparse_weight?: number;
}

export interface Citation {
  file: string;
  line_start?: number;
  line_end?: number;
  symbol?: string;
  chunk_id?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  created_at: string;
  updated_at?: string;
}
