import Simulation from "../components/Simulation";
import Sidebar from "../components/Sidebar";

function SimulationPage() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* 좌측 사이드바 영역 */}
      <div className="w-64 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <Simulation />
      </div>
    </div>
  );
}

export default SimulationPage;
