// App.js
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Sidebar from './components/Sidebar';
import Simulation from "./components/Simulation";
import AgvRegister from "./components/AgvRegister";

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-white">
        {/* 좌측 사이드바 영역 */}
        <div className="w-80 border-r border-gray-200">
         
          <Sidebar />
        </div>

        {/* 우측 메인 컨텐츠 영역 */}
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/monitor" element={<div>실시간 모니터링</div>} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/agv" element={<AgvRegister />} />
            <Route path="/admin" element={<div>관리자 정보 수정</div>} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
