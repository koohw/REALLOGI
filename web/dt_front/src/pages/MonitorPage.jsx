import React from "react";
import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";

function MonitorPage() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* 좌측 사이드바 영역 */}
      <div className="w-64 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1">
          <div className="flex justify-between items-center px-6 py-4 border-b w-full h-4/5">
            <AGVMap />
          </div>
        </div>
        {/* 여기에 하단 컨텐츠를 추가할 수 있습니다 */}
      </div>
    </div>
  );
}

export default MonitorPage;
