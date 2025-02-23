import React, { useState, useEffect } from "react";
import { agvService } from "../../api/agvService";

export default function AgvTable() {
  const [agvs, setAgvs] = useState([]);

  useEffect(() => {
    const eventSource = agvService.getAgvStream();

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setAgvs(data.agvs);
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const formatTime = (timeString) => {
    const date = new Date(timeString);
    return `${String(date.getHours()).padStart(2, "0")}:${String(
      date.getMinutes()
    ).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
  };

  const getWorkStatus = (agv) => {
    if (agv.state === "RUNNING") return "정상 가동";
    if (agv.state === "LOADING") return "화물 적재중";
    if (agv.state === "STOPPED") return "일시 정지";
    return "-";
  };

  const getOperationStatus = (agv) => {
    if (agv.issue) return agv.issue;
    if (agv.state === "LOADING") return "적재/하역";
    return "-";
  };

  const getLocation = (agv) => {
    return `(${agv.location_x}, ${agv.location_y})`;
  };

  const getEfficiencyClass = (efficiency) => {
    if (efficiency >= 80) return "text-green-400";
    if (efficiency >= 50) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <div className="bg-[#0D1B2A] rounded-lg shadow-lg p-6 border border-[#11263f]">
      <h2 className="text-lg font-semibold mb-4 text-white">AGV 상태</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[#11263f] border-b border-[#11263f]">
              <th className="px-4 py-3 text-left text-white font-medium">
                시간
              </th>
              <th className="px-4 py-3 text-left text-white font-medium">
                AGV 이름
              </th>
              <th className="px-4 py-3 text-left text-white font-medium">
                위치
              </th>
              <th className="px-4 py-3 text-left text-white font-medium">
                이동 효율성
              </th>
              <th className="px-4 py-3 text-left text-white font-medium">
                작업상태
              </th>
              <th className="px-4 py-3 text-left text-white font-medium">
                구동상태
              </th>
            </tr>
          </thead>
          <tbody>
            {agvs.map((agv) => (
              <tr
                key={agv.agv_id}
                className="border-b border-[#11263f]/30 hover:bg-[#11263f]/30 transition-colors"
              >
                <td className="px-4 py-3 text-gray-300">
                  {formatTime(agv.realtime)}
                </td>
                <td className="px-4 py-3 text-white font-medium">
                  {agv.agv_name}
                </td>
                <td className="px-4 py-3 text-gray-300">{getLocation(agv)}</td>
                <td
                  className={`px-4 py-3 font-medium ${getEfficiencyClass(
                    agv.efficiency
                  )}`}
                >
                  {agv.efficiency.toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-gray-300">
                  {getWorkStatus(agv)}
                </td>
                <td className="px-4 py-3 text-gray-300">
                  {getOperationStatus(agv)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
