import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { io } from "socket.io-client";

const Modal = ({ isOpen, onClose, children, title }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-[#11263f] rounded-lg p-6 max-w-lg w-full mx-4 relative border border-gray-700">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-200"
        >
          ✕
        </button>
        <h2 className="text-xl font-bold mb-4 text-gray-200">{title}</h2>
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
  const mapContainerRef = useRef(null);
  const [scale, setScale] = useState(1);
  const [agvData, setAgvData] = useState({ agv_count: 0, agvs: [] });
  const [speed, setSpeed] = useState(1);
  const [isRunning, setIsRunning] = useState(false);
  const [agvCount, setAgvCount] = useState(3);
  const [connectionStatus, setConnectionStatus] = useState("연결 중...");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const socketRef = useRef(null);
  const previousPositionsRef = useRef(new Map());

  const BASE_CELL_SIZE = 40;
  const MAP_WIDTH = mapData[0].length * BASE_CELL_SIZE;
  const MAP_HEIGHT = mapData.length * BASE_CELL_SIZE;

  // Calculate scale based on container size
  useEffect(() => {
    const updateScale = () => {
      if (mapContainerRef.current) {
        const containerWidth = mapContainerRef.current.clientWidth;
        const containerHeight = mapContainerRef.current.clientHeight;

        const scaleX = containerWidth / MAP_WIDTH;
        const scaleY = containerHeight / MAP_HEIGHT;

        // Use the smaller scale to ensure the entire map fits
        const newScale = Math.min(scaleX, scaleY, 1);
        setScale(newScale);
      }
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, [MAP_WIDTH, MAP_HEIGHT]);

  const CELL_SIZE = BASE_CELL_SIZE * scale;

  const getAGVColor = (agvId, currentX, currentY) => {
    const prevPosition = previousPositionsRef.current.get(agvId);
    if (!prevPosition) {
      previousPositionsRef.current.set(agvId, { x: currentX, y: currentY });
      return "bg-green-500"; // 초기 상태는 이동 중으로 간주
    }

    const isMoving = prevPosition.x !== currentX || prevPosition.y !== currentY;
    previousPositionsRef.current.set(agvId, { x: currentX, y: currentY });
    return isMoving ? "bg-green-500" : "bg-orange-500";
  };

  const getCellStyle = (cellType) => {
    const baseStyle = {
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
    };

    switch (cellType) {
      case 0:
        return {
          ...baseStyle,
          backgroundColor: "#11263f",
        };
      case 1:
        return {
          ...baseStyle,
          backgroundImage: "url(/images/box.jpg)",
        };
      case 2:
        return {
          backgroundColor: "#0D1B2A",
        };
      default:
        return {
          backgroundColor: "#11263f",
        };
    }
  };

  // Socket connection and event handlers remain the same
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
      socket.on("simulation_final", handleSimulationFinal); // Add this line
      socket.on("disconnect", handleDisconnect);
      socket.on("error", handleError);

      return socket;
    };

    const socket = initializeSocket();
    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [serverUrl]);

  // Event handlers remain the same
  const handleSimulationFinal = useCallback((result) => {
    setIsAnalyzing(false);
    setAnalysisResult(result);
    setShowAnalysisModal(true);
  }, []);

  // "심층 분석" 버튼: 서버의 REPEAT_RUNS(15회) 반복실험 결과 요청
  const requestDeepAnalysis = useCallback(() => {
    if (socketRef.current?.connected) {
      setIsAnalyzing(true);
      setAnalysisResult(null);
      socketRef.current.emit("simulate_final", {
        agv_count: agvCount,
        duration: 3000,
        initial_speed: speed,
        output: "final",
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
      const x = agv.location_y * BASE_CELL_SIZE;
      const y = agv.location_x * BASE_CELL_SIZE;

      return (
        <div
          key={agv.agv_id}
          className="absolute transition-all duration-100 flex items-center justify-center"
          style={{
            left: `${x}px`,
            top: `${y}px`,
            width: `${BASE_CELL_SIZE}px`,
            height: `${BASE_CELL_SIZE}px`,
            // Removed extra scaling here
          }}
        >
          <div
            className="relative"
            style={{ transform: `rotate(${agv.direction || 0}deg)` }}
          >
            <div
              className={`w-8 h-8 rounded-full ${getAGVColor(
                agv.agv_id,
                agv.location_x,
                agv.location_y
              )} flex items-center justify-center shadow-md`}
            >
              <div className="w-2 h-2 bg-white rounded-full" />
            </div>
            <span className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 text-xs font-bold">
              {agv.agv_id}
            </span>
          </div>
        </div>
      );
    });
  }, [agvData, BASE_CELL_SIZE]);
  return (
    <div className="p-3 border border-gray-700 rounded-lg bg-[#11263f] shadow-lg">
      {/* Controls Row */}
      <div className="flex items-center gap-3 mb-3">
        {/* Connection Status */}
        <span
          className={`px-2 py-0.5 rounded-full text-xs ${
            connectionStatus === "연결됨"
              ? "bg-green-900 text-green-200"
              : connectionStatus === "연결 중..."
              ? "bg-yellow-900 text-yellow-200"
              : "bg-red-900 text-red-200"
          }`}
        >
          {connectionStatus}
        </span>

        {/* AGV Count */}
        <div className="flex items-center text-sm text-gray-200">
          <span className="mr-1">AGV:</span>
          <input
            type="number"
            min="1"
            max="10"
            value={agvCount}
            onChange={handleAgvCountChange}
            className="w-16 px-1.5 py-0.5 border border-gray-700 rounded text-sm bg-[#0D1B2A] text-gray-200"
          />
        </div>

        {/* Speed Selection */}
        <div className="flex items-center text-sm text-gray-200">
          <span className="mr-1">Speed:</span>
          <select
            value={speed}
            onChange={handleSpeedChange}
            className="w-16 px-1.5 py-0.5 border border-gray-700 rounded text-sm bg-[#0D1B2A] text-gray-200"
            disabled={connectionStatus !== "연결됨"}
          >
            <option value={1}>1x</option>
            <option value={2}>2x</option>
            <option value={4}>4x</option>
            <option value={8}>8x</option>
            <option value={16}>16x</option>
          </select>
        </div>

        {/* Current AGVs info */}
        <div className="text-xs text-gray-400">
          Current AGVs: {agvData.agv_count || 0}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={requestDeepAnalysis}
            className="px-2 py-1 rounded text-sm bg-blue-900 text-gray-200 hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 border border-gray-700"
            disabled={connectionStatus !== "연결됨" || isAnalyzing}
          >
            {isAnalyzing ? (
              <>
                <svg
                  className="animate-spin h-3 w-3 text-gray-200"
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
                분석중
              </>
            ) : (
              "심층 분석"
            )}
          </button>
          <button
            onClick={toggleSimulation}
            className={`px-2 py-1 rounded text-sm ${
              isRunning ? "bg-red-900" : "bg-green-900"
            } text-gray-200 hover:opacity-90 border border-gray-700`}
            disabled={connectionStatus !== "연결됨"}
          >
            {isRunning ? "Stop" : "Start"}
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div
        ref={mapContainerRef}
        className="relative h-96 border border-gray-700 rounded-lg bg-[#0D1B2A] overflow-hidden"
      >
        <div
          className="relative"
          style={{
            width: `${MAP_WIDTH}px`,
            height: `${MAP_HEIGHT}px`,
            transform: `scale(${scale})`,
            transformOrigin: "top left",
          }}
        >
          {mapData.map((row, y) =>
            row.map((cell, x) => (
              <div
                key={`${y}-${x}`}
                style={{
                  ...getCellStyle(cell),
                  position: "absolute",
                  left: x * BASE_CELL_SIZE,
                  top: y * BASE_CELL_SIZE,
                  width: BASE_CELL_SIZE,
                  height: BASE_CELL_SIZE,
                }}
              />
            ))
          )}
          {renderAGVs}
        </div>
      </div>

      {/* Analysis Result Modal */}
      <Modal
        isOpen={showAnalysisModal}
        onClose={() => setShowAnalysisModal(false)}
        title="시뮬레이션 결과"
      >
        {analysisResult && (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold mb-2 text-gray-200">
                AGV 운영 통계
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">시간당 처리량</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.throughput_per_hour.toFixed(1)}건/시간
                  </div>
                </div>
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">AGV당 배송량</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.delivered_per_agv.toFixed(1)}건
                  </div>
                </div>
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">평균 사이클 타임</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.avg_cycle.toFixed(1)}초
                  </div>
                </div>
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">AGV 수</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.agv_count}대
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">처리량 표준편차</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.std_throughput_per_hour.toFixed(1)}건/시간
                  </div>
                </div>
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">배송량 표준편차</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.std_delivered_per_agv.toFixed(1)}건
                  </div>
                </div>
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">총 반복실험 횟수</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.repeat_runs}회
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="bg-[#0D1B2A] p-3 rounded border border-gray-700">
                  <div className="text-sm text-gray-400">평균 AGV 가동률</div>
                  <div className="text-lg font-semibold text-gray-200">
                    {analysisResult.avg_utilization.toFixed(2)}
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
