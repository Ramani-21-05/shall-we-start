// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/context/AuthContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Sidebar } from '@/components/layout/Sidebar'
import { AuthPage } from '@/pages/AuthPage'
import { HackathonDashboard } from '@/pages/HackathonDashboard'
import { Dashboard } from '@/pages/Dashboard'
import { ForecastPage } from '@/pages/ForecastPage'
import { PastPerformancePage } from '@/pages/PastPerformancePage'
import { ExplainabilityPage } from '@/pages/ExplainabilityPage'
import { AnomalyPage } from '@/pages/AnomalyPage'
import { StrategyPage } from '@/pages/StrategyPage'
import { AdminUsersPage } from '@/pages/AdminUsersPage'
import { LogsPage } from '@/pages/LogsPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Standalone Login Page */}
            <Route path="/login" element={<AuthPage />} />

            {/* Main Application Layout with Sidebar & Protected Routes */}
            <Route
              path="/*"
              element={
                <div className="flex">
                  <Sidebar />
                  <main className="main-content flex-1">
                    <Routes>
                      <Route
                        path="/"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN', 'MARKETING']}>
                            <Dashboard />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/dashboard"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN', 'MARKETING']}>
                            <Dashboard />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/strategy"
                        element={
                          <ProtectedRoute allowedRoles={['MARKETING']}>
                            <StrategyPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/simulation"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
                            <HackathonDashboard />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/forecast"
                        element={
                          <ProtectedRoute allowedRoles={['MARKETING']}>
                            <ForecastPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/performance"
                        element={
                          <ProtectedRoute allowedRoles={['MARKETING']}>
                            <PastPerformancePage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/explainability"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN']}>
                            <ExplainabilityPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/anomaly"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN']}>
                            <AnomalyPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/admin/users"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN']}>
                            <AdminUsersPage />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/admin/logs"
                        element={
                          <ProtectedRoute allowedRoles={['ADMIN']}>
                            <LogsPage />
                          </ProtectedRoute>
                        }
                      />
                    </Routes>
                  </main>
                </div>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
