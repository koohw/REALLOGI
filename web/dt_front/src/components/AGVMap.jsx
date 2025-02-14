import React, { useState, useEffect, useRef } from "react";
import {
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Circle,
} from "lucide-react";
import { agvService } from "../api/agvService";
import AGVControlPanel from "./AGVControlPanel";
import TileMap from "./TileMap";

const AGVMap = ({ onStateChange }) => {
  // Add onStateChange prop here
  const [agvData, setAgvData] = useState([]);
  const [lastUpdate, setLastUpdate] = useState("");
  const agvPositions = useRef(new Map());
  const cellSize = 25;

  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedAgvs, setSelectedAgvs] = useState([]);

  const mapData = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
  ];

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

    const eventSource = agvService.getAgvStream();
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.success && data.agvs) {
        data.agvs.forEach((newAgv) => {
          const currentPos = agvPositions.current.get(newAgv.agv_id);
          if (currentPos) {
            if (
              currentPos.x !== newAgv.location_y ||
              currentPos.y !== newAgv.location_x
            ) {
              updateAGVPosition(
                newAgv.agv_id,
                currentPos.x,
                currentPos.y,
                newAgv.location_y,
                newAgv.location_x,
                1000
              );
            }
          }
          agvPositions.current.set(newAgv.agv_id, {
            x: newAgv.location_y,
            y: newAgv.location_x,
          });
        });

        setAgvData(data.agvs);
        // Call onStateChange prop with updated AGV data
        if (onStateChange) {
          onStateChange(data.agvs);
        }
        setLastUpdate(data.agvs[0]?.realtime || "");
      }
    };

    return () => {
      eventSource.close();
    };
  }, [onStateChange]); // Add onStateChange to dependency array

  // Rest of your component code...
  const handleAgvClick = (agv, e) => {
    e.stopPropagation();
    setSelectedAgvs((prev) => {
      const isSelected = prev.some(
        (selected) => selected.agv_id === agv.agv_id
      );
      if (isSelected) {
        return prev.filter((selected) => selected.agv_id !== agv.agv_id);
      } else {
        return [...prev, agv];
      }
    });
  };

  const handleMapClick = () => {
    setSelectedAgvs([]);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((prevScale) =>
      Math.max(0.5, Math.min(prevScale * scaleFactor, 4))
    );
  };

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

  const getDirectionArrow = (direction) => {
    switch (direction?.toLowerCase()) {
      case "u":
        return <ArrowUp className="text-white" size={10} />;
      case "d":
        return <ArrowDown className="text-white" size={10} />;
      case "l":
        return <ArrowLeft className="text-white" size={10} />;
      case "r":
        return <ArrowRight className="text-white" size={10} />;
      default:
        return <Circle className="text-white" size={8} />;
    }
  };

  const getAGVColor = (state) => {
    switch (state?.toUpperCase()) {
      case "RUNNING":
        return "#22c55e";
      case "STOPPED":
        return "#EF4444";
      case "EMERGENCY(STOPPED)":
        return "#DC2626";
      case "LOADING":
        return "#F59E0B";
      case "UNLOADING":
        return "#F59E0B";
      default:
        return "#6B7280";
    }
  };

  const formatTime = (timeString) => {
    if (!timeString) return "";
    const date = new Date(timeString);
    return date.toLocaleTimeString();
  };

  return (
    <div className="flex gap-4 h-full w-full">
      <div className="flex-1 flex flex-col">
        <div className="mb-1 text-sm text-gray-600">
          Last Update: {formatTime(lastUpdate)}
        </div>
        <div
          className="relative overflow-hidden border rounded-lg shadow-lg flex-1"
          onClick={handleMapClick}
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
            <TileMap mapData={mapData} cellSize={cellSize} />

            {agvData.map((agv) => {
              const initialPos = agvPositions.current.get(agv.agv_id) || {
                x: agv.location_y,
                y: agv.location_x,
              };
              const isSelected = selectedAgvs.some(
                (selected) => selected.agv_id === agv.agv_id
              );

              return (
                <div
                  id={`agv-${agv.agv_id}`}
                  key={agv.agv_id}
                  className={`absolute flex items-center justify-center rounded-full cursor-pointer
                    ${isSelected ? "ring-2 ring-blue-500 ring-offset-2" : ""}`}
                  style={{
                    width: cellSize * 0.8,
                    height: cellSize * 0.8,
                    left: cellSize * 0.1,
                    top: cellSize * 0.1,
                    transform: `translate(${initialPos.x * cellSize}px, ${
                      initialPos.y * cellSize
                    }px)`,
                    backgroundColor: getAGVColor(agv.state),
                    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    willChange: "transform",
                    transition: "background-color 0.3s ease",
                  }}
                  onClick={(e) => handleAgvClick(agv, e)}
                >
                  <div className="transform transition-transform duration-300">
                    {getDirectionArrow(agv.direction)}
                  </div>
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-1 py-0.2 rounded-full text-[8px] font-medium shadow-sm">
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

      <div className="w-96 flex-shrink-0">
        <AGVControlPanel
          selectedAgvs={selectedAgvs}
          onActionComplete={() => setSelectedAgvs([])}
        />
      </div>
    </div>
  );
};

export default AGVMap;
