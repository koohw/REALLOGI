import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import {
  startOperation,
  initializeOperation,
} from "../features/operationSlice";
import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";
import VideoPopup from "../components/VideoPopup";
import { agvService } from "../api/agvService";

function MonitorPage() {
  const operationStarted = useSelector(
    (state) => state.operation.operationStarted
  );
  const dispatch = useDispatch();
  const [showVideo, setShowVideo] = useState(false);
  const [showControls, setShowControls] = useState(true);

  const handleAgvStateChange = (agvData) => {
    const emergencyAgv = agvData.find(
      (agv) => agv.state === "EMERGENCY(STOPPED)"
    );
    if (emergencyAgv) {
      setShowVideo(true);
    }
  };

  const handleOperationClick = async () => {
    if (!operationStarted) {
      // 작업 시작
      try {
        const response = await agvService.startAgv();
        console.log("작업 시작 응답:", response);
        dispatch(startOperation());
      } catch (error) {
        console.error("작업 시작 에러:", error);
        dispatch(startOperation());
      }
    } else {
      // 작업 초기화
      try {
        const response = await agvService.initializeAgv();
        console.log("작업 초기화 응답:", response);
        dispatch(initializeOperation());
      } catch (error) {
        console.error("작업 초기화 에러:", error);
        dispatch(initializeOperation());
      }
    }
  };

  return (
    <div className="flex min-h-screen bg-[#0D1B2A]">
      {/* Left sidebar area */}
      <div className="w-64 border-r border-gray-700">
        <Sidebar />
      </div>

      {/* Right main content area */}
      <div className="flex-1 flex flex-col">
        {/* Header with controls */}
        <div className="p-4 border-b border-gray-700 bg-[#11263f] flex justify-between items-center">
          {/* 작업 시작 / 작업 초기화 버튼 */}
          <button
            onClick={handleOperationClick}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            {operationStarted ? "작업 초기화" : "작업 시작"}
          </button>

          {/* View Toggle Buttons */}
          <div className="inline-flex rounded-lg bg-gray-800 p-1">
            <button
              className={`px-4 py-2 rounded-lg transition-colors ${
                showControls
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
              onClick={() => setShowControls(true)}
            >
              분석
            </button>
            <button
              className={`px-4 py-2 rounded-lg transition-colors ${
                !showControls
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
              onClick={() => setShowControls(false)}
            >
              제어
            </button>
          </div>
        </div>

        <div className="flex-1 bg-[#11263f]">
          <div className="flex justify-between items-center px-6 py-4 border-b border-gray-700 w-full h-full">
            <AGVMap
              onStateChange={handleAgvStateChange}
              showControls={showControls}
            />
          </div>
        </div>
      </div>
      {showVideo && <VideoPopup onClose={() => setShowVideo(false)} />}
    </div>
  );
}

export default MonitorPage;
