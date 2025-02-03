import React, { useState, useEffect } from "react";
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from "lucide-react";

const AGVMap = () => {
  const [agvData, setAgvData] = useState([]);
  const cellSize = 50; // 각 셀의 크기

  const mapData = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    [0, 1, 0, 0, 0, 1, 1, 0, 1, 0],
    [0, 1, 1, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 1, 1, 0],
    [0, 1, 1, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 1, 1, 1, 0, 1, 0],
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
  ];

  useEffect(() => {
    const eventSource = new EventSource("http://localhost:5000/api/agv-stream"); // SSE 엔드포인트 URL

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.success && data.agv) {
        setAgvData(data.agv);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const getDirectionArrow = (direction) => {
    switch (direction) {
      case "U":
        return <ArrowUp className="text-white" size={20} />;
      case "D":
        return <ArrowDown className="text-white" size={20} />;
      case "L":
        return <ArrowLeft className="text-white" size={20} />;
      case "R":
        return <ArrowRight className="text-white" size={20} />;
      default:
        return null;
    }
  };

  return (
    <div className="p-4">
      <div
        className="relative"
        style={{ width: cellSize * 10, height: cellSize * 10 }}
      >
        {/* Map Grid */}
        {mapData.map((row, y) => (
          <div key={y} className="flex">
            {row.map((cell, x) => (
              <div
                key={`${x}-${y}`}
                className={`
                  w-12 h-12 border border-gray-300
                  ${cell === 1 ? "bg-gray-200" : "bg-white"}
                `}
              />
            ))}
          </div>
        ))}

        {/* AGVs */}
        {agvData.map((agv) => (
          <div
            key={agv.agv_id}
            className="absolute flex items-center justify-center rounded-full bg-blue-500 transition-all duration-500"
            style={{
              width: cellSize * 0.8,
              height: cellSize * 0.8,
              left: `${agv.location_x * cellSize + cellSize * 0.1}px`,
              top: `${agv.location_y * cellSize + cellSize * 0.1}px`,
            }}
          >
            {getDirectionArrow(agv.direction)}
            <span className="text-white text-xs absolute -top-4">
              {agv.agv_name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AGVMap;
