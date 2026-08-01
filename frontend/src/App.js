import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { Toaster } from 'sonner';
import WhiteRoom from './pages/WhiteRoom';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import WarRoom from './pages/WarRoom';
import ErrorBoundary from './components/ErrorBoundary';
import '@/App.css';

// Component to handle path persistence and restoration
function PathRestorer() {
  const location = useLocation();
  const { setLastPath } = useApp();

  // Save current path whenever it changes (for future use if needed)
  useEffect(() => {
    if (location.pathname !== '/') {
      setLastPath(location.pathname);
    }
  }, [location.pathname, setLastPath]);

  // Removed auto-navigation - users should start fresh from search
  // This prevents stale localStorage data from causing errors
  return null;
}

function AppContent() {
  return (
    <>
      <PathRestorer />
      <div className="App">
        <Routes>
          <Route path="/" element={<WhiteRoom />} />
          <Route path="/dashboard" element={<ExecutiveDashboard />} />
          <Route path="/war-room" element={<WarRoom />} />
        </Routes>
        <Toaster
          position="top-right"
          theme="dark"
          toastOptions={{
            style: {
              background: '#121212',
              border: '1px solid #262626',
              color: '#E5E5E5',
              fontFamily: 'JetBrains Mono, monospace'
            }
          }}
        />
      </div>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  );
}

export default App;
