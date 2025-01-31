// App.js
import { BrowserRouter, Routes, Route } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import SimulationPage from "./pages/SimulationPage";
import AgvRegisterPage from "./pages/AgvRegisterPage";
import ModifyInfoPage from "./pages/ModifyInfoPage";
import MonitorPage from "./pages/MonitorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
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
  );
}

export default App;
