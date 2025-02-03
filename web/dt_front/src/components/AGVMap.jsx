import React, { useState, useEffect, useRef } from "react";

const AGVMap = () => {
  const [agvData, setAgvData] = useState([]);
  const [interpolatedPositions, setInterpolatedPositions] = useState({});
  const animationFrameRef = useRef();
  const previousPositionsRef = useRef({});
  const cellSize = 50;

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
    // 초기 더미 데이터
    const initialData = [
      {
        agv_id: 1,
        agv_name: "AGV1",
        state: "fine",
        issue: "",
        location_x: 3,
        location_y: 2,
      },
      {
        agv_id: 2,
        agv_name: "AGV2",
        state: "fine",
        issue: "",
        location_x: 4,
        location_y: 1,
      },
      {
        agv_id: 3,
        agv_name: "AGV3",
        state: "fine",
        issue: "",
        location_x: 3,
        location_y: 6,
      },
      {
        agv_id: 4,
        agv_name: "AGV4",
        state: "fine",
        issue: "",
        location_x: 4,
        location_y: 9,
      },
    ];

    setAgvData(initialData);
    initializeInterpolatedPositions(initialData);

    const eventSource = new EventSource("http://localhost:5000/api/agv-stream");
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.success && data.agv) {
        updateAgvPositions(data.agv);
      }
    };

    return () => {
      eventSource.close();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const initializeInterpolatedPositions = (initialData) => {
    const positions = {};
    initialData.forEach((agv) => {
      positions[agv.agv_id] = {
        x: agv.location_x * cellSize,
        y: agv.location_y * cellSize,
      };
    });
    setInterpolatedPositions(positions);
    previousPositionsRef.current = positions;
  };

  const updateAgvPositions = (newAgvData) => {
    setAgvData((prevData) => {
      const updatedData = prevData.map((prevAgv) => {
        const updatedAgv = newAgvData.find(
          (newAgv) => newAgv.agv_id === prevAgv.agv_id
        );
        return updatedAgv || prevAgv;
      });

      startInterpolation(updatedData);
      return updatedData;
    });
  };

  const startInterpolation = (newData) => {
    const startTime = performance.now();
    const duration = 1000; // 1초 동안 애니메이션
    const startPositions = { ...previousPositionsRef.current };
    const targetPositions = {};

    newData.forEach((agv) => {
      targetPositions[agv.agv_id] = {
        x: agv.location_x * cellSize,
        y: agv.location_y * cellSize,
      };
    });

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function for smooth movement
      const eased =
        progress < 0.5
          ? 4 * progress * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      const newPositions = {};
      Object.keys(targetPositions).forEach((agvId) => {
        const start = startPositions[agvId];
        const target = targetPositions[agvId];

        newPositions[agvId] = {
          x: start.x + (target.x - start.x) * eased,
          y: start.y + (target.y - start.y) * eased,
        };
      });

      setInterpolatedPositions(newPositions);

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        previousPositionsRef.current = targetPositions;
      }
    };

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    animationFrameRef.current = requestAnimationFrame(animate);
  };

  return (
    <div className="p-4">
      <div
        className="relative bg-white rounded-lg shadow-lg"
        style={{
          width: cellSize * mapData[0].length,
          height: cellSize * mapData.length,
        }}
      >
        {/* 맵 배경 */}
        {mapData.map((row, y) => (
          <div key={`row-${y}`} className="flex" style={{ height: cellSize }}>
            {row.map((cell, x) => (
              <div
                key={`cell-${x}-${y}`}
                className={`
                  ${cell === 1 ? "bg-gray-100" : "bg-white"}
                `}
                style={{
                  width: cellSize,
                  height: cellSize,
                }}
              />
            ))}
          </div>
        ))}

        {/* AGV 표시 */}
        {agvData.map((agv) => {
          const position = interpolatedPositions[agv.agv_id] || {
            x: agv.location_x * cellSize,
            y: agv.location_y * cellSize,
          };

          return (
            <div
              key={agv.agv_id}
              className="absolute w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center"
              style={{
                left: position.x,
                top: position.y,
                width: cellSize * 0.8,
                height: cellSize * 0.8,
                transform: "translate(10%, 10%)",
                transition: "left 0.5s ease-out, top 0.5s ease-out",
              }}
            >
              <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-2 py-0.5 rounded text-xs whitespace-nowrap">
                {agv.agv_name}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AGVMap;
