import React from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { DashboardShell } from './components/layout/DashboardShell';
import { OverviewPage } from './pages/dashboard/OverviewPage';
import { FilesPage } from './pages/dashboard/FilesPage';
import { ChatPage } from './pages/dashboard/ChatPage';

const App: React.FC = () => (
  <BrowserRouter>
    <Routes>
      {/* Home — also serves as the repository connection entry point */}
      <Route path="/" element={<HomePage />} />

      {/* /ingest is no longer a standalone page; redirect to home */}
      <Route path="/ingest" element={<Navigate to="/" replace />} />

      {/* Dashboard — nested under the shell */}
      <Route path="/dashboard/:repoId" element={<DashboardShell />}>
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="files"    element={<FilesPage />} />
        <Route path="chat"     element={<ChatPage />} />
      </Route>

      {/* Catch-all fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
);

export default App;
