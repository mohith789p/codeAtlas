import type { Repository } from './repositories';
import type { FileNode } from './files';
import type { ChatMessage } from './chat';

class DashboardCache {
  private repositories = new Map<string, Repository>();
  private fileTrees = new Map<string, FileNode[]>();
  private fileContents = new Map<string, { content: string; language: string }>();
  private chatSessions = new Map<string, string>();
  private chatMessages = new Map<string, ChatMessage[]>();

  // Repository
  getRepository(repoId: string): Repository | null {
    return this.repositories.get(repoId) ?? null;
  }

  setRepository(repoId: string, repo: Repository): void {
    this.repositories.set(repoId, repo);
  }

  // File Tree
  getTree(repoId: string): FileNode[] | null {
    return this.fileTrees.get(repoId) ?? null;
  }

  setTree(repoId: string, tree: FileNode[]): void {
    this.fileTrees.set(repoId, tree);
  }

  // File Content
  getFile(repoId: string, path: string): { content: string; language: string } | null {
    return this.fileContents.get(`${repoId}:${path}`) ?? null;
  }

  setFile(repoId: string, path: string, content: string, language: string): void {
    this.fileContents.set(`${repoId}:${path}`, { content, language });
  }

  // Chat Sessions & Messages
  getSessionId(repoId: string): string | null {
    return this.chatSessions.get(repoId) ?? null;
  }

  setSessionId(repoId: string, sessionId: string): void {
    this.chatSessions.set(repoId, sessionId);
  }

  getMessages(repoId: string): ChatMessage[] | null {
    return this.chatMessages.get(repoId) ?? null;
  }

  setMessages(repoId: string, messages: ChatMessage[]): void {
    this.chatMessages.set(repoId, messages);
  }

  clear(repoId?: string): void {
    if (repoId) {
      this.repositories.delete(repoId);
      this.fileTrees.delete(repoId);
      this.chatSessions.delete(repoId);
      this.chatMessages.delete(repoId);
      for (const key of Array.from(this.fileContents.keys())) {
        if (key.startsWith(`${repoId}:`)) {
          this.fileContents.delete(key);
        }
      }
    } else {
      this.repositories.clear();
      this.fileTrees.clear();
      this.fileContents.clear();
      this.chatSessions.clear();
      this.chatMessages.clear();
    }
  }
}

export const dashboardCache = new DashboardCache();
