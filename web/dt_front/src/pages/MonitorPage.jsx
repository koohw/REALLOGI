import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";
import VideoPopup from "../components/VideoPopup";

function MonitorPage() {
  const [showVideo, setShowVideo] = useState(false);

  const handleAgvStateChange = (agvData) => {
    const emergencyAgv = agvData.find(
      (agv) => agv.state === "EMERGENCY(STOPPED)"
    );
    if (emergencyAgv) {
      setShowVideo(true);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#0D1B2A]">
      {" "}
      {/* 배경색 변경 */}
      {/* Left sidebar area */}
      <div className="w-64 border-r border-gray-700">
        {" "}
        {/* 테두리 색상 어둡게 */}
        <Sidebar />
      </div>
      {/* Right main content area */}
      <div className="flex-1 flex flex-col">
        {/* Test Button */}
        <div className="p-4 border-b border-gray-700 bg-[#11263f]">
          {" "}
          {/* 배경색과 테두리 변경 */}
          <button
            onClick={() => setShowVideo(!showVideo)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            {showVideo ? "비디오 닫기" : "비디오 열기"}
          </button>
        </div>

        <div className="flex-1 bg-[#11263f]">
          {" "}
          {/* 배경색 변경 */}
          <div className="flex justify-between items-center px-6 py-4 border-b border-gray-700 w-full h-4/5">
            <AGVMap onStateChange={handleAgvStateChange} />
          </div>
        </div>
      </div>
      {showVideo && <VideoPopup onClose={() => setShowVideo(false)} />}
    </div>
  );
}

export default MonitorPage;
