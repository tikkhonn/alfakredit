import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { useAuth } from './lib/auth'
import { ApplicationPage } from './pages/ApplicationPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { NewApplicationPage } from './pages/NewApplicationPage'
import { SpecialistDossierPage } from './pages/SpecialistDossierPage'
import { SpecialistQueuePage } from './pages/SpecialistQueuePage'
import type { ReactNode } from 'react'

function Gate({ role, children }: { role?: 'client' | 'specialist'; children: ReactNode }) {
  const { me, loading } = useAuth()
  if (loading) return <div className="grid min-h-svh place-items-center text-muted-foreground">Собираем кабинет…</div>
  if (!me) return <Navigate to="/login" replace />
  if (role && me.role !== role) return <Navigate to={me.role === 'specialist' ? '/bank' : '/'} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Gate>
            <AppShell />
          </Gate>
        }
      >
        <Route
          path="/"
          element={
            <Gate role="client">
              <DashboardPage />
            </Gate>
          }
        />
        <Route
          path="/new"
          element={
            <Gate role="client">
              <NewApplicationPage />
            </Gate>
          }
        />
        <Route
          path="/applications/:id"
          element={
            <Gate role="client">
              <ApplicationPage />
            </Gate>
          }
        />
        <Route
          path="/bank"
          element={
            <Gate role="specialist">
              <SpecialistQueuePage />
            </Gate>
          }
        />
        <Route
          path="/bank/:id"
          element={
            <Gate role="specialist">
              <SpecialistDossierPage />
            </Gate>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
