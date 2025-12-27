import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ChatsPage from './pages/ChatsPage';
import ChatDetailPage from './pages/ChatDetailPage';
import SettingsPage from './pages/SettingsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import NotFoundPage from './pages/NotFoundPage';
import './index.css';

const queryClient = new QueryClient();

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false);
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const token = useAuthStore(state => state.token);

  console.log('[APP] PrivateRoute render:', { 
    isReady, 
    isAuthenticated, 
    hasToken: !!token 
  });

  useEffect(() => {
    console.log('[APP] PrivateRoute useEffect running...');
    const init = async () => {
      console.log('[APP] Starting initialization...');
      await new Promise(resolve => setTimeout(resolve, 100));
      console.log('[APP] Initialization complete, setIsReady(true)');
      setIsReady(true);
    };
    init();
  }, []);

  console.log('[APP] PrivateRoute rendering:', { isReady, isAuthenticated });

  if (!isReady) {
    console.log('[APP] Showing loading screen');
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    console.log('[APP] Not authenticated, redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  console.log('[APP] Authenticated, rendering children');
  return <>{children}</>;
}

export default function App() {
  console.log('[APP] App component render');

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<DashboardPage />} />
            <Route path="chats" element={<ChatsPage />} />
            <Route path="chats/:id" element={<ChatDetailPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
