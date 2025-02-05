import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { io } from "socket.io-client";
import { Truck } from "lucide-react";

const Modal = ({ isOpen, onClose, children, title }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
        <h2 className="text-xl font-bold mb-4">{title}</h2>
        {children}
      </div>
    </div>
  );
};

// 서버의 맵 데이터와 동일하게 설정
const DEFAULT_MAP = [
  [2, 2, 2, 2, 2, 2, 2],
  [0, 0, 0, 0, 0, 0, 0],
  [0, 1, 0, 1, 0, 1, 0],
  [0, 1, 0, 1, 0, 1, 0],
  [0, 0, 0, 0, 0, 0, 0],
  [0, 1, 0, 1, 0, 1, 0],
  [0, 1, 0, 1, 0, 1, 0],
  [0, 0, 0, 0, 0, 0, 0],
  [2, 2, 2, 2, 2, 2, 2],
];

const AGVMonitoring = ({ mapData = DEFAULT_MAP, serverUrl }) => {
  const [agvData, setAgvData] = useState({ agv_count: 0, agvs: [] });
  const [speed, setSpeed] = useState(1);
  const [isRunning, setIsRunning] = useState(false);
  const [agvCount, setAgvCount] = useState(3);
  const [connectionStatus, setConnectionStatus] = useState("연결 중...");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const socketRef = useRef(null);
  const mapContainerRef = useRef(null);

  // Map dimensions
  const CELL_SIZE = 40;
  const MAP_WIDTH = mapData[0].length * CELL_SIZE;
  const MAP_HEIGHT = mapData.length * CELL_SIZE;

  const getCellStyle = (cellType) => {
    switch (cellType) {
      case 1: // 벽
        return "bg-gray-200";
      case 2: // 작업 구역 (선반/출구)
        return "bg-blue-100";
      default: // 빈 공간
        return "";
    }
  };

  const getAGVColor = (status) => {
    switch (status) {
      case "active":
        return "text-blue-500";
      case "idle":
        return "text-gray-400";
      case "error":
        return "text-red-500";
      default:
        return "text-blue-500";
    }
  };

  useEffect(() => {
    const initializeSocket = () => {
      const serverAddress = new URL(serverUrl);

      const socket = io(serverAddress.origin, {
        path: "/socket.io",
        transports: ["websocket"],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 2000,
      });

      socket.on("connect", () => {
        setConnectionStatus("연결됨");
        sendCurrentConfig(socket);
      });

      socket.on("message", handleSocketMessage);
      socket.on("disconnect", handleDisconnect);
      socket.on("error", handleError);
      socket.on("analysis_result", handleAnalysisResult);

      return socket;
    };

    const socket = initializeSocket();
    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [serverUrl]);

  const handleAnalysisResult = useCallback((result) => {
    setIsAnalyzing(false);
    setAnalysisResult(result);
    setShowAnalysisModal(true);
  }, []);

  const requestAnalysis = useCallback(() => {
    if (socketRef.current?.connected) {
      setIsAnalyzing(true);
      setAnalysisResult(null);
      socketRef.current.emit("message", {
        command: "analyze",
        agv_count: agvCount,
        speed,
      });
    }
  }, [agvCount, speed]);

  const sendCurrentConfig = useCallback(
    (socket = socketRef.current) => {
      if (socket?.connected) {
        const config = {
          speed,
          agv_count: agvCount,
          command: isRunning ? "update" : "init",
        };
        socket.emit("message", config);
      }
    },
    [speed, agvCount, isRunning]
  );

  const handleSocketMessage = useCallback((data) => {
    if (!data.type) {
      setAgvData(data);
    }
  }, []);

  const handleDisconnect = useCallback(() => {
    setConnectionStatus("재연결 중...");
  }, []);

  const handleError = useCallback(() => {
    setConnectionStatus("연결 오류");
  }, []);

  const handleAgvCountChange = useCallback(
    (event) => {
      const newCount = parseInt(event.target.value);
      setAgvCount(newCount);

      if (socketRef.current?.connected) {
        const message = {
          agv_count: newCount,
          speed,
          command: "init",
        };
        socketRef.current.emit("message", message);
      }
    },
    [speed]
  );

  const handleSpeedChange = useCallback(
    (event) => {
      const newSpeed = Number(event.target.value);
      setSpeed(newSpeed);

      if (socketRef.current?.connected) {
        const message = {
          speed: newSpeed,
          agv_count: agvCount,
          command: "update",
        };
        socketRef.current.emit("message", message);
      }
    },
    [agvCount]
  );

  const toggleSimulation = useCallback(() => {
    const newIsRunning = !isRunning;
    setIsRunning(newIsRunning);

    if (socketRef.current?.connected) {
      const message = {
        command: newIsRunning ? "start" : "stop",
        agv_count: agvCount,
        speed,
      };
      socketRef.current.emit("message", message);
    }
  }, [isRunning, agvCount, speed]);

  const renderAGVs = useMemo(() => {
    if (!agvData.agvs?.length) return null;

    return agvData.agvs.map((agv) => {
      const x = agv.location_x * CELL_SIZE;
      const y = agv.location_y * CELL_SIZE;

      return (
        <div
          key={agv.agv_id}
          className="absolute transition-all duration-100 flex items-center justify-center"
          style={{
            left: `${x}px`,
            top: `${y}px`,
            width: `${CELL_SIZE}px`,
            height: `${CELL_SIZE}px`,
          }}
        >
          <div
            className="relative"
            style={{
              transform: `rotate(${agv.direction || 0}deg)`,
            }}
          >
            <Truck className={`w-8 h-8 ${getAGVColor(agv.status)}`} />
            <span className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 text-xs font-bold">
              {agv.agv_id}
            </span>
          </div>
        </div>
      );
    });
  }, [agvData, CELL_SIZE]);

  return (
    <div className="p-4 border rounded-lg bg-white shadow-lg">
      {/* Controls */}
      <div className="space-y-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span
            className={`px-3 py-1 rounded-full text-sm ${
              connectionStatus === "연결됨"
                ? "bg-green-100 text-green-800"
                : connectionStatus === "연결 중..."
                ? "bg-yellow-100 text-yellow-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {connectionStatus}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={requestAnalysis}
              className="px-4 py-2 rounded-md bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              disabled={connectionStatus !== "연결됨" || isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  분석중...
                </>
              ) : (
                "즉시 분석"
              )}
            </button>
            <button
              onClick={toggleSimulation}
              className={`px-4 py-2 rounded-md ${
                isRunning ? "bg-red-500" : "bg-green-500"
              } text-white`}
              disabled={connectionStatus !== "연결됨"}
            >
              {isRunning ? "Stop" : "Start"}
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <label className="flex items-center">
            <span className="mr-2">AGV Count:</span>
            <input
              type="number"
              min="1"
              max="10"
              value={agvCount}
              onChange={handleAgvCountChange}
              className="w-20 px-2 py-1 border rounded"
            />
          </label>

          <label className="flex items-center">
            <span className="mr-2">Speed:</span>
            <select
              value={speed}
              onChange={handleSpeedChange}
              className="w-24 px-2 py-1 border rounded"
              disabled={connectionStatus !== "연결됨"}
            >
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
              <option value={8}>8x</option>
              <option value={16}>16x</option>
            </select>
          </label>
        </div>

        <div className="text-sm text-gray-600">
          Current AGVs: {agvData.agv_count || 0}
        </div>
      </div>

      {/* Map Container */}
      <div
        className="relative h-96 overflow-auto border border-gray-200 rounded-lg"
        ref={mapContainerRef}
      >
        <div
          className="relative"
          style={{
            width: `${MAP_WIDTH}px`,
            height: `${MAP_HEIGHT}px`,
            background: "#f8f9fa",
          }}
        >
          {/* Map Background */}
          {mapData.map((row, y) =>
            row.map(
              (cell, x) =>
                cell !== 0 && (
                  <div
                    key={`${y}-${x}`}
                    className={`absolute ${getCellStyle(cell)}`}
                    style={{
                      left: x * CELL_SIZE,
                      top: y * CELL_SIZE,
                      width: CELL_SIZE,
                      height: CELL_SIZE,
                    }}
                  />
                )
            )
          )}

          {/* AGVs Layer */}
          {renderAGVs}
        </div>
      </div>

      {/* Analysis Result Modal */}
      <Modal
        isOpen={showAnalysisModal}
        onClose={() => setShowAnalysisModal(false)}
        title="AGV 운영 분석 결과"
      >
        {analysisResult && (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold mb-2">AGV 운영 통계</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">평균 이동 거리</div>
                  <div className="text-lg font-semibold">
                    {analysisResult.avgDistance}m
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">평균 속도</div>
                  <div className="text-lg font-semibold">
                    {analysisResult.avgSpeed}m/s
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">총 운행 시간</div>
                  <div className="text-lg font-semibold">
                    {analysisResult.totalTime}초
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">충돌 위험 횟수</div>
                  <div className="text-lg font-semibold">
                    {analysisResult.collisionRisks}회
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AGVMonitoring;
