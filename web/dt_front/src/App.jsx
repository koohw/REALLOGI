import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import Dashboard from './components/Dashboard';
import Simulation from './components/Simulation';
import { ProtectedLayout, PublicLayout } from './Layout';
import AgvRegister from './components/AgvRegister';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800" />
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route
          path="/login"
          element={
            <PublicLayout>
              {user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
            </PublicLayout>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicLayout>
              {user ? <Navigate to="/dashboard" replace /> : <SignupPage />}
            </PublicLayout>
          }
        />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedLayout>
              <Dashboard />
            </ProtectedLayout>
          }
        />
        <Route
          path="/monitor"
          element={
            <ProtectedLayout>
              <div>실시간 모니터링</div>
            </ProtectedLayout>
          }
        />
        <Route
          path="/simulation"
          element={
            <ProtectedLayout>
              <Simulation />
            </ProtectedLayout>
          }
        />
        <Route
          path="/agv"
          element={
            <ProtectedLayout>
              <AgvRegister/>
            </ProtectedLayout>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedLayout>
              <div>관리자 정보 수정</div>
            </ProtectedLayout>
          }
        />

        {/* Default Redirect */}
        <Route
          path="/"
          element={<Navigate to={user ? "/dashboard" : "/login"} replace />}
        />
      </Routes>
    </Router>
  );
}

export default App;