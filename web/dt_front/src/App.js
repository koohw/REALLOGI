// src/App.js
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Provider, useDispatch } from "react-redux";
import store, { persistor } from "./store";
import DashboardPage from "./pages/DashboardPage";
import SimulationPage from "./pages/SimulationPage";
import AgvRegisterPage from "./pages/AgvRegisterPage";
import ModifyInfoPage from "./pages/ModifyInfoPage";
import MonitorPage from "./pages/MonitorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { PersistGate } from "redux-persist/integration/react";
import { rehydrate } from "./features/userSlice";
import { useEffect } from "react";

function App() {
  return (
    <Provider store={store}>
      <PersistGate loading={null} persistor={persistor}>
        <MainApp />
      </PersistGate>
    </Provider>
  );
}

// 🔹 Redux와 관련된 로직을 별도 컴포넌트로 분리
function MainApp() {
  const dispatch = useDispatch();

  useEffect(() => {
    const persistedState = localStorage.getItem("persist:user");
    if (persistedState) {
      try {
        const parsedState = JSON.parse(persistedState);
        dispatch(rehydrate(parsedState));
      } catch (error) {
        console.error("Failed to parse persisted state:", error);
      }
    }
  }, [dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
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
  );
}

export default App;
