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
          <div className="flex justify-between items-center px-6 py-4 border-b w-full">
            <AGVMap />
            <div className="flex flex-col space-y-2">
              <button className="m-2 bg-blue-500 text-white px-4 py-2 rounded">
                버튼1
              </button>
              <button className="m-2 bg-green-500 text-white px-4 py-2 rounded">
                버튼2
              </button>
              <button className="m-2 bg-red-500 text-white px-4 py-2 rounded">
                버튼3
              </button>
            </div>
          </div>
          <div className="flex-1 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-800">
              AGV 모니터링
            </h2>
            <div className="mt-4">
              {/* 여기에 AGV 모니터링 컴포넌트를 추가할 수 있습니다 */}
            </div>
          </div>
        </div>
        {/* 여기에 하단 컨텐츠를 추가할 수 있습니다 */}
      </div>
    </div>
  );
}

export default MonitorPage;
