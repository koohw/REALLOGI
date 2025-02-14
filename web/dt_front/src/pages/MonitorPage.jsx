import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";
import VideoPopup from "../components/VideoPopup";

function MonitorPage() {
  const [showVideo, setShowVideo] = useState(false);

  // AGV 상태 변경 핸들러 - 비디오 표시 용도로만 사용
  const handleAgvStateChange = (agvData) => {
    const emergencyAgv = agvData.find(
      (agv) => agv.state === "EMERGENCY(STOPPED)"
    );
    if (emergencyAgv) {
      setShowVideo(true);
    }
  };

  return (
    <div className="flex min-h-screen bg-white">
      {/* Left sidebar area */}
      <div className="w-64 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* Right main content area */}
      <div className="flex-1 flex flex-col">
        {/* Test Button */}
        <div className="p-4 border-b">
          <button
            onClick={() => setShowVideo(!showVideo)}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
          >
            {showVideo ? "비디오 닫기" : "비디오 열기"}
          </button>
        </div>

        <div className="flex-1">
          <div className="flex justify-between items-center px-6 py-4 border-b w-full h-4/5">
            <AGVMap onStateChange={handleAgvStateChange} />
          </div>
        </div>
      </div>

      {/* Video Popup */}
      {showVideo && <VideoPopup onClose={() => setShowVideo(false)} />}
    </div>
  );
}

export default MonitorPage;
