// components/AGVSelectionInfo.jsx
import React from "react";

const AGVSelectionInfo = ({ selectedAgvs }) => {
  if (selectedAgvs.length === 0) {
    return null;
  }

  const getStateColor = (state) => {
    switch (state?.toUpperCase()) {
      case "RUNNING":
        return "bg-green-100 text-green-800";
      case "STOPPED":
        return "bg-red-100 text-red-800";
      case "EMERGENCY":
        return "bg-red-100 text-red-800";
      case "UNLOADING":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="mt-4">
      <div className="text-sm font-medium text-gray-700 mb-2">
        선택된 AGV 목록
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {selectedAgvs.map((agv) => (
          <div
            key={agv.agv_id}
            className="flex items-center justify-between p-2 bg-gray-50 rounded-md hover:bg-gray-100"
          >
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="font-medium">{agv.agv_name}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`px-2 py-1 rounded-full text-xs ${getStateColor(
                  agv.state
                )}`}
              >
                {agv.state}
              </span>
              <span className="text-sm text-gray-500">issue: {agv.issue}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AGVSelectionInfo;
