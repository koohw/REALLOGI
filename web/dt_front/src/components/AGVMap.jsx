import React, { useState, useEffect, useRef } from "react";
import { Circle, Maximize2, Minimize2 } from "lucide-react";
import { agvService } from "../api/agvService";
import TileMap from "./TileMap";
import AGVControlPanel from "./AGVControlPanel";
import AnalyticsView from "./AnalyticsView";
import { useDispatch } from "react-redux";
import {
  updateAGVData,
  updateOrderTotal,
  updateOrderSuccess,
} from "../features/agvSlice";
const AGVMap = ({ onStateChange, showControls }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const mapContainerRef = useRef(null);
  const [agvData, setAgvData] = useState([]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState("");
  const agvPositions = useRef(new Map());
  const cellSize = 50;

  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedAgvs, setSelectedAgvs] = useState([]);
  const dispatch = useDispatch();

  const mapData = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
  ];

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      mapContainerRef.current.requestFullscreen().catch((err) => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    let isSubscribed = true;

    const interpolatePosition = (startX, startY, endX, endY, progress) => ({
      x: startX + (endX - startX) * progress,
      y: startY + (endY - startY) * progress,
    });

    const updateAGVPosition = (agvId, startX, startY, endX, endY, duration) => {
      const startTime = performance.now();

      const animate = (currentTime) => {
        if (!isSubscribed) return;

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
      if (!isSubscribed) return;
      const data = JSON.parse(event.data);

      if (data.success && data.agvs) {
        // Update AGV positions and animations
        data.agvs.forEach((newAgv) => {
          const currentPos = agvPositions.current.get(newAgv.agv_id);
          if (currentPos) {
            const newX = newAgv.location_y;
            const newY = newAgv.location_x;

            if (currentPos.x !== newX || currentPos.y !== newY) {
              updateAGVPosition(
                newAgv.agv_id,
                currentPos.x,
                currentPos.y,
                newX,
                newY,
                1000
              );
            }
          }

          agvPositions.current.set(newAgv.agv_id, {
            x: newAgv.location_y,
            y: newAgv.location_x,
          });
        });

        // Update local state
        setAgvData(data.agvs);
        setLastUpdate(data.agvs[0]?.realtime || "");

        // Update Redux store
        const timestamp = new Date(data.overall_efficiency_history[0][0]);
        const timeLabel = `${String(timestamp.getHours()).padStart(
          2,
          "0"
        )}:${String(timestamp.getMinutes()).padStart(2, "0")}:${String(
          timestamp.getSeconds()
        ).padStart(2, "0")}`;

        dispatch(
          updateAGVData({
            time: timeLabel,
            efficiency: data.overall_efficiency,
          })
        );

        const orderTotal = Object.values(data.order_success).reduce(
          (sum, count) => sum + count,
          0
        );
        dispatch(updateOrderTotal(orderTotal));
        dispatch(updateOrderSuccess(data.order_success));

        // Call onStateChange if provided
        if (onStateChange) {
          onStateChange(data.agvs);
        }
      }
    };

    // eventSource.onerror = (error) => {
    //   console.error("SSE Error:", error);
    //   if (isSubscribed) {
    //     eventSource.close();
    //   }
    // };

    return () => {
      isSubscribed = false;
      eventSource.close();
    };
  }, [dispatch, onStateChange]);
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
    return <Circle className="text-white" size={16} />;
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
    <div
      className={`flex gap-4 ${
        isFullscreen ? "h-screen w-screen p-4 bg-[#11263f]" : "h-full w-full"
      }`}
    >
      <div className="flex-1 flex flex-col relative">
        <button
          onClick={toggleFullscreen}
          className="absolute top-4 right-4 z-10 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-white transition-colors"
          title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
        >
          {isFullscreen ? (
            <Minimize2 className="w-5 h-5" />
          ) : (
            <Maximize2 className="w-5 h-5" />
          )}
        </button>

        <div
          ref={mapContainerRef}
          className="relative overflow-hidden border border-gray-700 rounded-lg shadow-lg flex-1"
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

            {/* AGV markers */}
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
                    width: cellSize * 0.3,
                    height: cellSize * 0.3,
                    left: cellSize * 0.4,
                    top: cellSize * 0.4,
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
                  <div className="absolute -top-5 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-1 py-0.2 rounded-full text-[12px] font-medium shadow-sm">
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
        <div className="mb-1 text-sm text-gray-600">
          Last Update: {formatTime(lastUpdate)}
        </div>
      </div>

      {!isFullscreen && (
        <div className="w-96 flex-shrink-0">
          {showControls ? (
            <AnalyticsView agvData={analyticsData} />
          ) : (
            <AGVControlPanel
              selectedAgvs={selectedAgvs}
              onActionComplete={() => setSelectedAgvs([])}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default AGVMap;
