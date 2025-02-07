import AGVMonitoring from "../components/AGVMonitoring";
import Sidebar from "../components/Sidebar";

function SimulationPage() {
  const maps = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
  ];

  return (
    <div className="flex min-h-screen bg-white">
      {/* 좌측 사이드바 영역 */}
      <div className="w-64 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <div className="grid grid-cols-2 gap-4 p-4 bg-gray-100">
          <AGVMonitoring mapData={maps} serverUrl="http://localhost:5001" />
          <AGVMonitoring mapData={maps} serverUrl="http://localhost:5002" />
          <AGVMonitoring mapData={maps} serverUrl="http://localhost:5003" />
          <AGVMonitoring mapData={maps} serverUrl="http://localhost:5004" />
        </div>
      </div>
    </div>
  );
}

export default SimulationPage;
