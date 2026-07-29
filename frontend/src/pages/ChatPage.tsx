import React, { useState, useEffect, useRef } from 'react';
import { useRepo } from '../context/RepoContext';
import api from '../api/client';
import { ChatSession, ChatMessage } from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { MessageSquare, Plus, Send, Bot, User, FileCode, Sparkles, Loader2 } from 'lucide-react';

export const ChatPage: React.FC = () => {
  const { activeRepo } = useRepo();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchSessions = async () => {
    if (!activeRepo) return;
    try {
      const res = await api.get<ChatSession[]>(`/chat/sessions?repo_id=${activeRepo.id}`);
      setSessions(res.data);
      if (res.data.length > 0 && !activeSession) {
        setActiveSession(res.data[0]);
      }
    } catch (err) {
      console.error('Failed to load chat sessions', err);
    }
  };

  const fetchMessages = async (sessionId: number) => {
    try {
      const res = await api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
      setMessages(res.data);
    } catch (err) {
      console.error('Failed to load messages', err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [activeRepo]);

  useEffect(() => {
    if (activeSession) {
      fetchMessages(activeSession.id);
    }
  }, [activeSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleCreateSession = async () => {
    if (!activeRepo) return;
    try {
      const res = await api.post<ChatSession>('/chat/sessions', {
        repo_id: activeRepo.id,
        title: `Repo Query ${sessions.length + 1}`,
      });
      setSessions([res.data, ...sessions]);
      setActiveSession(res.data);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create chat session', err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || sending) return;

    let currentSess = activeSession;
    if (!currentSess && activeRepo) {
      // Auto-create session if none active
      const res = await api.post<ChatSession>('/chat/sessions', {
        repo_id: activeRepo.id,
        title: query.substring(0, 30),
      });
      currentSess = res.data;
      setSessions([res.data, ...sessions]);
      setActiveSession(res.data);
    }

    if (!currentSess) return;

    const userText = query;
    setQuery('');
    setSending(true);

    // Optimistic UI push user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await api.post<ChatMessage>('/chat/query', {
        session_id: currentSess.id,
        query: userText,
      });
      setMessages((prev) => [...prev, res.data]);
    } catch (err) {
      console.error('Error sending query', err);
    } finally {
      setSending(false);
    }
  };

  if (!activeRepo) {
    return (
      <div className="p-8 text-center text-slate-400">
        Please select or upload a repository to start RAG Q&A.
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] p-6 flex gap-6 overflow-hidden">
      {/* Session History Sidebar */}
      <div className="w-72 glass-panel rounded-2xl p-4 flex flex-col border border-slate-800 flex-shrink-0">
        <button
          onClick={handleCreateSession}
          className="gradient-btn w-full py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 mb-4"
        >
          <Plus className="w-4 h-4" />
          <span>New Conversation</span>
        </button>

        <div className="text-[11px] font-semibold uppercase text-slate-500 tracking-wider mb-2 px-2">
          Chat History
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {sessions.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-6">No chat sessions yet.</div>
          ) : (
            sessions.map((sess) => (
              <button
                key={sess.id}
                onClick={() => setActiveSession(sess)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-medium flex items-center space-x-2.5 transition ${
                  activeSession?.id === sess.id
                    ? 'bg-indigo-600/25 text-indigo-300 border border-indigo-500/30 font-semibold'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-indigo-400" />
                <span className="truncate">{sess.title}</span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main RAG Chat Interface */}
      <div className="flex-1 glass-panel rounded-2xl flex flex-col border border-slate-800 overflow-hidden">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-3 text-slate-500">
              <Bot className="w-12 h-12 text-indigo-400/80 animate-pulse" />
              <h3 className="text-base font-bold text-slate-200">Ask CodeAtlas RAG AI</h3>
              <p className="text-xs max-w-sm text-slate-400">
                Ask how specific endpoints, database queries, or domain algorithms work in this repository.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-3xl rounded-2xl p-4 text-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none shadow-lg shadow-indigo-600/20'
                      : 'glass-card border border-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <div>
                      <MarkdownRenderer content={msg.content} />

                      {/* Source Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2">
                          <div className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                            <span>Retrieved Code Sources</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {msg.sources.map((src, i) => (
                              <div
                                key={i}
                                className="px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-indigo-300 flex items-center space-x-1.5"
                              >
                                <FileCode className="w-3 h-3 text-indigo-400" />
                                <span>
                                  [{src.source_index}] {src.file_path}:{src.start_line}-{src.end_line}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs flex-shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {sending && (
            <div className="flex gap-4 items-center text-indigo-400 text-xs font-mono">
              <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <span>Searching code vectors & generating response...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSendMessage} className="p-4 bg-slate-900/80 border-t border-slate-800 flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about this software repository..."
            className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={!query.trim() || sending}
            className="gradient-btn px-5 rounded-xl font-semibold flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
