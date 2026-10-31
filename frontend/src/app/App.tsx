import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AppRouter } from './router';

export const App: React.FC = () => (
  <BrowserRouter>
    <AppRouter />
  </BrowserRouter>
);

export default App;
