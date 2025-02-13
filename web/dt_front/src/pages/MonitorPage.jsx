import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";
import EmergencyPopup from "../components/EmergencyPopup";

function MonitorPage() {
  const [emergencyAgv, setEmergencyAgv] = useState(null);

  // Callback function to handle AGV state changes
  const handleAgvStateChange = (agvData) => {
    const emergencyAgv = agvData.find(
      (agv) => agv.state === "EMERGENCY(STOPPED)"
    );
    if (emergencyAgv) {
      setEmergencyAgv(emergencyAgv);
    }
  };

  const testEmergencyAgv = {
    agv_id: "TEST001",
    agv_name: "AGV-TEST",
    state: "EMERGENCY(STOPPED)",
    location_x: 5,
    location_y: 3,
    direction: "N",
    issue: "테스트용 긴급 정지",
    realtime: new Date().toISOString(),
  };

  return (
    <div className="flex min-h-screen bg-white">
      {/* Left sidebar area */}
      <div className="w-64 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* Right main content area */}
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b">
          <button
            onClick={() => setEmergencyAgv(testEmergencyAgv)}
            className="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
          >
            테스트 팝업 띄우기
          </button>
        </div>

        <div className="flex-1">
          <div className="flex justify-between items-center px-6 py-4 border-b w-full h-4/5">
            <AGVMap onStateChange={handleAgvStateChange} />
          </div>
        </div>
      </div>

      {/* Emergency Popup */}
      {emergencyAgv && (
        <EmergencyPopup
          agv={emergencyAgv}
          onClose={() => setEmergencyAgv(null)}
        />
      )}
    </div>
  );
}

export default MonitorPage;
