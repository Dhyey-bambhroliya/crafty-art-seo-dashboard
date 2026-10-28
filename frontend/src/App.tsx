import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { LoginPage } from './pages/LoginPage';
import { SetupManagerPage } from './pages/SetupManagerPage';
import { DashboardPage } from './pages/DashboardPage';
import { CategoryManagementPage } from './pages/CategoryManagementPage';
import { CategoryDetailPage } from './pages/CategoryDetailPage';
import { PagesMonitoringPage } from './pages/PagesMonitoringPage';
import { PageDetailPage } from './pages/PageDetailPage';
import { AlertsPage } from './pages/AlertsPage';
import { TeamManagementPage } from './pages/TeamManagementPage';
import { GSCConnectionPage } from './pages/GSCConnectionPage';
import { SyncHistoryPage } from './pages/SyncHistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { FestivalDashboardPage } from './pages/FestivalDashboardPage';
import { FestivalDetailPage } from './pages/FestivalDetailPage';
import { FestivalTasksPage } from './pages/FestivalTasksPage';

// Protected Route Guard
const ProtectedRoute: React.FC<{ children: React.ReactNode; managerOnly?: boolean }> = ({
  children,
  managerOnly = false,
}) => {
  const { isAuthenticated, isLoading, role } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (managerOnly && role !== 'MANAGER') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Authentication Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/setup" element={<SetupManagerPage />} />
          <Route path="/gsc-callback" element={<GSCConnectionPage />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/categories" element={<CategoryManagementPage />} />
            <Route path="/categories/:id" element={<CategoryDetailPage />} />
            <Route path="/pages" element={<PagesMonitoringPage />} />
            <Route path="/pages/:id" element={<PageDetailPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route
              path="/team"
              element={
                <ProtectedRoute managerOnly={true}>
                  <TeamManagementPage />
                </ProtectedRoute>
              }
            />
            <Route path="/gsc-connection" element={<GSCConnectionPage />} />
            <Route path="/sync-history" element={<SyncHistoryPage />} />
            <Route path="/festivals" element={<FestivalDashboardPage />} />
            <Route path="/festivals/tasks" element={<FestivalTasksPage />} />
            <Route path="/festivals/:id" element={<FestivalDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
