import React, { useState, useEffect, useRef } from "react";
import {
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Circle,
} from "lucide-react";

const AGVMap = () => {
  const [agvData, setAgvData] = useState([]);
  const [lastUpdate, setLastUpdate] = useState("");
  const agvPositions = useRef(new Map());
  const cellSize = 25;

  // 확대/축소 및 드래그 상태 관리
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // const mapData = [
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  //   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  // ];

  const mapData = [
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
    [
      0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
      1, 0, 1, 0, 1,
    ],
    [
      1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
      0, 1, 0, 1, 0,
    ],
  ];

  // 확대/축소 핸들러
  const handleWheel = (e) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((prevScale) =>
      Math.max(0.5, Math.min(prevScale * scaleFactor, 4))
    );
  };

  // 드래그 핸들러
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // 기존 AGV 위치 업데이트 로직
  useEffect(() => {
    const interpolatePosition = (startX, startY, endX, endY, progress) => {
      return {
        x: startX + (endX - startX) * progress,
        y: startY + (endY - startY) * progress,
      };
    };

    const updateAGVPosition = (agvId, startX, startY, endX, endY, duration) => {
      const startTime = performance.now();
      const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const { x, y } = interpolatePosition(
          startX,
          startY,
          endX,
          endY,
          progress
        );
        const agvElement = document.getElementById(`agv-${agvId}`);
        if (agvElement) {
          agvElement.style.transform = `translate(${x * cellSize}px, ${
            y * cellSize
          }px)`;
        }

        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };

      requestAnimationFrame(animate);
    };

    const initialData = {
      success: true,
      agv_number: 4,
      agv: [
        {
          agv_id: 1,
          agv_name: "agv1",
          state: "fine",
          issue: "",
          location_x: 2,
          location_y: 0,
          direction: "R",
        },
        {
          agv_id: 2,
          agv_name: "agv2",
          state: "fine",
          issue: "",
          location_x: 5,
          location_y: 2,
          direction: "D",
        },
        {
          agv_id: 3,
          agv_name: "agv3",
          state: "fine",
          issue: "",
          location_x: 6,
          location_y: 1,
          direction: "U",
        },
        {
          agv_id: 4,
          agv_name: "agv4",
          state: "fine",
          issue: "",
          location_x: 4,
          location_y: 3,
          direction: "D",
        },
      ],
    };

    initialData.agv.forEach((agv) => {
      agvPositions.current.set(agv.agv_id, {
        x: agv.location_x,
        y: agv.location_y,
      });
    });

    setAgvData(initialData.agv);

    const eventSource = new EventSource("http://localhost:5000/api/agv-stream");
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.success && data.agv) {
        data.agv.forEach((newAgv) => {
          const currentPos = agvPositions.current.get(newAgv.agv_id);
          if (currentPos) {
            if (
              currentPos.x !== newAgv.location_x ||
              currentPos.y !== newAgv.location_y
            ) {
              updateAGVPosition(
                newAgv.agv_id,
                currentPos.x,
                currentPos.y,
                newAgv.location_x,
                newAgv.location_y,
                1000
              );
            }
            agvPositions.current.set(newAgv.agv_id, {
              x: newAgv.location_x,
              y: newAgv.location_y,
            });
          }
        });

        setAgvData(data.agv);
        setLastUpdate(data.agv[0]?.realtime || "");
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const getDirectionArrow = (direction) => {
    switch (direction) {
      case "U":
        return <ArrowUp className="text-white" size={10} />;
      case "D":
        return <ArrowDown className="text-white" size={10} />;
      case "L":
        return <ArrowLeft className="text-white" size={10} />;
      case "R":
        return <ArrowRight className="text-white" size={10} />;
      case "NONE":
        return <Circle className="text-white" size={8} />;
      default:
        return <Circle className="text-white" size={8} />;
    }
  };

  const getAGVColor = (state) => {
    switch (state) {
      case "fine":
        return "#22c55e";
      default:
        return "#EF4444";
    }
  };

  const formatTime = (timeString) => {
    if (!timeString) return "";
    const date = new Date(timeString);
    return date.toLocaleTimeString();
  };

  return (
    <div className="flex-1">
      <div className="mb-1 text-sm text-gray-600">
        Last Update: {formatTime(lastUpdate)}
      </div>
      {/* 확대/축소 및 드래그 가능한 컨테이너 */}
      <div
        className="relative overflow-hidden border rounded-lg shadow-lg"
        style={{
          width: "100% - 2rem",
          height: "calc(100vh - 400px)",
        }}
      >
        <div
          className="absolute w-full h-full cursor-move"
          style={{
            transform: `scale(${scale}) translate(${position.x}px, ${position.y}px)`,
            transformOrigin: "0 0",
            willChange: "transform",
          }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* Map Background */}
          <div className="absolute top-0 left-0 w-full h-full">
            {mapData.map((row, y) => (
              <div
                key={`row-${y}`}
                className="flex"
                style={{ height: cellSize }}
              >
                {row.map((cell, x) => (
                  <div
                    key={`cell-${x}-${y}`}
                    className={cell === 1 ? "bg-gray-100" : "bg-white"}
                    style={{
                      width: cellSize,
                      height: cellSize,
                    }}
                  />
                ))}
              </div>
            ))}
          </div>

          {/* AGVs */}
          {agvData.map((agv) => {
            const initialPos = agvPositions.current.get(agv.agv_id) || {
              x: agv.location_x,
              y: agv.location_y,
            };
            return (
              <div
                id={`agv-${agv.agv_id}`}
                key={agv.agv_id}
                className="absolute flex items-center justify-center rounded-full"
                style={{
                  width: cellSize * 0.8,
                  height: cellSize * 0.8,
                  left: cellSize * 0.1,
                  top: cellSize * 0.1,
                  transform: `translate(${(initialPos.x * cellSize) / 2}px, ${
                    (initialPos.y * cellSize) / 2
                  }px)`,
                  backgroundColor: getAGVColor(agv.state),
                  boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                  willChange: "transform",
                  transition: "background-color 0.3s ease",
                }}
              >
                <div className="transform transition-transform duration-300">
                  {getDirectionArrow(agv.direction)}
                </div>
                <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-2 py-0.5 rounded-full text-xs font-medium shadow-md">
                  {agv.agv_name}
                </div>
                {agv.issue && (
                  <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-2 py-0.5 rounded-full text-xs font-medium shadow-md">
                    {agv.issue}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AGVMap;
