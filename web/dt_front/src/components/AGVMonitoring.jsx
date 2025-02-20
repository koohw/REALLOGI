import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { io } from "socket.io-client";

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
  const socketRef = useRef(null);
  const previousPositionsRef = useRef(new Map());

  const BASE_CELL_SIZE = 40;
  const MAP_WIDTH = mapData[0].length * BASE_CELL_SIZE;
  const MAP_HEIGHT = mapData.length * BASE_CELL_SIZE;

  // 컨테이너 크기에 따른 scale 계산
  useEffect(() => {
    const updateScale = () => {
      if (mapContainerRef.current) {
        const containerWidth = mapContainerRef.current.clientWidth;
        const containerHeight = mapContainerRef.current.clientHeight;
        const scaleX = containerWidth / MAP_WIDTH;
        const scaleY = containerHeight / MAP_HEIGHT;
        const newScale = Math.min(scaleX, scaleY, 1);
        setScale(newScale);
      }
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, [MAP_WIDTH, MAP_HEIGHT]);

  const getAGVColor = (agvId, currentX, currentY) => {
    const prevPosition = previousPositionsRef.current.get(agvId);
    if (!prevPosition) {
      previousPositionsRef.current.set(agvId, { x: currentX, y: currentY });
      return "bg-green-500";
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
        return { ...baseStyle, backgroundColor: "#11263f" };
      case 1:
        return { ...baseStyle, backgroundImage: "url(/images/box.jpg)" };
      case 2:
        return { backgroundColor: "#0D1B2A" };
      default:
        return { backgroundColor: "#11263f" };
    }
  };

  // Socket 연결 및 이벤트 처리
  useEffect(() => {
    const initializeSocket = () => {
      const serverAddress = new URL(serverUrl);
      const socket = io(serverAddress.origin, {
        path: serverAddress.pathname,
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
      socket.on("simulation_final", handleSimulationFinal);
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

  const handleSimulationFinal = useCallback((result) => {
    setIsAnalyzing(false);
    setAnalysisResult(result);
  }, []);

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
          }}
        >
          <div
            className="relative"
            style={{ transform: `rotate(${agv.direction || 0}deg)` }}
          >
            <div
              className={`w-4 h-4 rounded-full ${getAGVColor(
                agv.agv_id,
                agv.location_x,
                agv.location_y
              )} flex items-center justify-center shadow-md`}
            >
              <div className="w-1 h-1 bg-white rounded-full" />
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
      {/* 컨트롤 영역 */}
      <div className="flex items-center gap-3 mb-3">
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
        <div className="text-xs text-gray-400">
          Current AGVs: {agvData.agv_count || 0}
        </div>
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

      {/* 지도 영역 */}
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
                className="flex items-center justify-center"
              >
                {cell === 0 && (
                  <div className="w-1 h-1 bg-gray-500 opacity-70 rounded-full" />
                )}
              </div>
            ))
          )}
          {renderAGVs}
        </div>

        {/* 결과 오버레이 영역 (지도 위에 표시) */}
        {analysisResult && (
          <div className="absolute inset-0 z-20 bg-[#11263f] bg-opacity-95 flex flex-col justify-center items-center">
            {/* 닫기 버튼 */}
            <button
              className="absolute top-2 right-2 text-gray-200 hover:text-gray-400 text-2xl"
              onClick={() => setAnalysisResult(null)}
            >
              ✕
            </button>
            <div className="w-full h-full p-4">
              {analysisResult.analysis_type === "single" ? (
                // 시뮬레이션 결과 (single 타입)
                <div className="grid grid-cols-3 grid-rows-3 gap-2 h-full">
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">시간당 처리량</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.throughput_per_hour.toFixed(1)}건/시간
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">AGV당 배송량</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.delivered_per_agv.toFixed(1)}건
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      평균 사이클 타임
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.avg_cycle.toFixed(1)}초
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      평균 대기 시간
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.avg_wait.toFixed(1)}초
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      평균 이동 시간
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.avg_travel.toFixed(1)}초
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">총 배송 수</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.delivered_count}건
                    </span>
                  </div>
                  {/* 남은 셀은 비워두거나 추가 정보를 넣을 수 있습니다 */}
                  <div className="bg-[#0D1B2A] p-2 border border-gray-700"></div>
                  <div className="bg-[#0D1B2A] p-2 border border-gray-700"></div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">전체 결과</span>
                  </div>
                </div>
              ) : (
                // AGV 운영 통계 (single 타입이 아닐 때)
                <div className="grid grid-cols-3 grid-rows-3 gap-2 h-full">
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">시간당 처리량</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.throughput_per_hour.toFixed(1)}건/시간
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">AGV당 배송량</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.delivered_per_agv.toFixed(1)}건
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      평균 사이클 타임
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.avg_cycle.toFixed(1)}초
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">AGV 수</span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.agv_count}대
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      처리량 표준편차
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.std_throughput_per_hour.toFixed(1)}건/시간
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      배송량 표준편차
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.std_delivered_per_agv.toFixed(1)}건
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      총 반복실험 횟수
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.repeat_runs}회
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">
                      평균 AGV 가동률
                    </span>
                    <span className="font-semibold text-gray-200 text-base">
                      {analysisResult.avg_utilization.toFixed(2)}
                    </span>
                  </div>
                  <div className="bg-[#0D1B2A] flex flex-col justify-center items-center p-2 border border-gray-700">
                    <span className="text-gray-400 text-xs">전체 결과</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AGVMonitoring;
