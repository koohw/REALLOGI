<<<<<<< HEAD
// App.js
import { BrowserRouter, Routes, Route } from "react-router-dom";
=======
// src/App.js
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Provider } from "react-redux";
import store from "./store";
>>>>>>> e71f8ea46ce89185e7502f21fb024b5c6826c008
import DashboardPage from "./pages/DashboardPage";
import SimulationPage from "./pages/SimulationPage";
import AgvRegisterPage from "./pages/AgvRegisterPage";
import ModifyInfoPage from "./pages/ModifyInfoPage";
import MonitorPage from "./pages/MonitorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
<<<<<<< HEAD
import Layout from "./Layout";
import PublicLayout from "./PublicLayout";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/agv-register" element={<AgvRegisterPage />} />
          <Route path="/monitor" element={<MonitorPage />} />
          <Route path="/simulation" element={<SimulationPage />} />
          <Route path="/modify-info" element={<ModifyInfoPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
=======
import { useAuth } from './hooks/useAuth';
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  const { user, loading } = useAuth(); // 인증 상태 확인

  if (loading) {
    return <div>Loading...</div>; // 인증 상태를 확인하는 동안 로딩 화면을 표시
  }

  return (
    <Provider store={store}>
      <BrowserRouter>
        <Routes>
        <Route
              path="/"
              element={user ? <DashboardPage /> : <Navigate to="/login" />}
            />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulation"
            element={
              <ProtectedRoute>
                <SimulationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agv-register"
            element={
              <ProtectedRoute>
                <AgvRegisterPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/modify-info"
            element={
              <ProtectedRoute>
                <ModifyInfoPage />
              </ProtectedRoute>
            }
          />
          <Route path="/monitor" element={<MonitorPage />} />
        </Routes>
      </BrowserRouter>
    </Provider>
>>>>>>> e71f8ea46ce89185e7502f21fb024b5c6826c008
  );
}

export default App;
