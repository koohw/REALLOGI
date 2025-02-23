// components/AGVSelectionInfo.jsx
import React from "react";

const AGVSelectionInfo = ({ selectedAgvs }) => {
  if (selectedAgvs.length === 0) {
    return null;
  }

  const getStateColor = (state) => {
    switch (state?.toUpperCase()) {
      case "RUNNING":
        return "bg-green-700 text-green-100"; // 어두운 테마에 맞게 조정
      case "STOPPED":
        return "bg-red-700 text-red-100";
      case "EMERGENCY":
        return "bg-red-700 text-red-100";
      case "UNLOADING":
        return "bg-yellow-700 text-yellow-100";
      default:
        return "bg-gray-700 text-gray-100";
    }
  };

  return (
    <div className="mt-4 bg-[#11263f] p-4 rounded-lg">
      {" "}
      {/* 배경색 추가 */}
      <div className="text-sm font-medium text-gray-200 mb-2">
        {" "}
        {/* 텍스트 색상 밝게 */}
        선택된 AGV 목록
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {selectedAgvs.map((agv) => (
          <div
            key={agv.agv_id}
            className="flex items-center justify-between p-2 bg-[#0D1B2A] rounded-md hover:bg-gray-800" /* 배경색 변경 */
          >
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="font-medium text-gray-200">
                {agv.agv_name}
              </span>{" "}
              {/* 텍스트 색상 밝게 */}
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`px-2 py-1 rounded-full text-xs ${getStateColor(
                  agv.state
                )}`}
              >
                {agv.state}
              </span>
              <span className="text-sm text-gray-400">issue: {agv.issue}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AGVSelectionInfo;
