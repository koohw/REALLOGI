import React from "react";
import AGVMonitoring from "../components/AGVMonitoring";
import Sidebar from "../components/Sidebar";

function SimulationPage() {
  const maps = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
  ];

  // 각 시뮬레이션 인스턴스를 고유한 serverUrl로 렌더링
  const simulationConfigs = [
    { id: 0, serverUrl: "http://localhost:5001" },
    { id: 1, serverUrl: "http://localhost:5002" },
    { id: 2, serverUrl: "http://localhost:5003" },
    { id: 3, serverUrl: "http://localhost:5004" },
  ];

  return (
    <div className="flex min-h-screen bg-[#0D1B2A]">
      {/* 좌측 사이드바 영역 */}
      <div className="w-64 border-r border-gray-700">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <div className="grid grid-cols-2 gap-4 p-4 bg-[#11263f]">
          {simulationConfigs.map((sim) => (
            <AGVMonitoring
              key={sim.id}
              mapData={maps}
              serverUrl={sim.serverUrl}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default SimulationPage;
