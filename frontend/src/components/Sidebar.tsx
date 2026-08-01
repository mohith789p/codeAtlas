import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FolderTree, MessageSquare, BookOpen, Search } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Overview', path: '/', icon: LayoutDashboard },
    { label: 'Code Explorer', path: '/explorer', icon: FolderTree },
    { label: 'RAG Q&A Chat', path: '/chat', icon: MessageSquare },
    { label: 'Documentation', path: '/docs', icon: BookOpen },
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-dark-900/60 p-4 flex flex-col justify-between flex-shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3">
          Navigation
        </div>
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-600/30 to-violet-600/20 text-indigo-300 border border-indigo-500/30 shadow-lg shadow-indigo-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="glass-card p-4 rounded-xl text-xs space-y-2 border border-slate-800">
        <div className="flex items-center space-x-2 text-indigo-400 font-semibold">
          <Search className="w-3.5 h-3.5" />
          <span>pgvector Enabled</span>
        </div>
        <p className="text-slate-400 leading-relaxed text-[11px]">
          CodeAtlas uses 3072-dim embeddings with cosine distance for instant RAG code retrieval.
        </p>
      </div>
    </aside>
  );
};
