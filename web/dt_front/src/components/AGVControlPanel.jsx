import React from "react";
import { Pause, RotateCcw, Play, X } from "lucide-react";
import { agvService } from "../api/agvService";
import Button from "./Button";
import AGVSelectionInfo from "./AGVSelectionInfo";

const AGVControlPanel = ({ selectedAgvs, onActionComplete, onDeselectAgv }) => {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleAction = async (action) => {
    if (selectedAgvs.length === 0) {
      setError("AGV를 선택해주세요.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const agvIds = selectedAgvs.map((agv) => agv.agv_id);
      let response;

      switch (action) {
        case "stop":
          response = await agvService.stopAgv(agvIds);
          break;
        case "return":
          response = await agvService.returnAgv(agvIds);
          break;
        case "restart":
          response = await agvService.restartAgv(agvIds);
          break;
        default:
          throw new Error("Invalid action");
      }

      if (!response.success) {
        throw new Error(response.message || "작업 실패");
      }

      if (onActionComplete) {
        onActionComplete();
      }
    } catch (err) {
      setError(err.message || "작업 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4 bg-[#11263f] rounded-lg shadow-lg border border-gray-700">
      {" "}
      {/* 배경색 및 테두리 변경 */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-200">AGV 제어 패널</h3>{" "}
        {/* 텍스트 색상 변경 */}
        {selectedAgvs.length > 0 && (
          <button
            onClick={onActionComplete}
            className="text-sm text-gray-400 hover:text-gray-200 flex items-center transition-colors" /* 텍스트 색상 변경 */
          >
            <X className="w-4 h-4 mr-1" />
            선택 해제
          </button>
        )}
      </div>
      {error && (
        <div className="p-3 mb-4 text-sm text-red-200 bg-red-900 bg-opacity-50 rounded-md border border-red-700">
          {" "}
          {/* 에러 메시지 스타일 변경 */}
          {error}
        </div>
      )}
      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={() => handleAction("stop")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1 bg-[#0D1B2A] hover:bg-gray-800 text-gray-200 border-gray-700" /* 버튼 스타일 변경 */
        >
          <Pause className="w-4 h-4 mr-2" />
          정지
        </Button>
        <Button
          variant="secondary"
          onClick={() => handleAction("return")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1 bg-[#0D1B2A] hover:bg-gray-800 text-gray-200 border-gray-700" /* 버튼 스타일 변경 */
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          복귀
        </Button>
        <Button
          variant="secondary"
          onClick={() => handleAction("restart")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1 bg-[#0D1B2A] hover:bg-gray-800 text-gray-200 border-gray-700" /* 버튼 스타일 변경 */
        >
          <Play className="w-4 h-4 mr-2" />
          재가동
        </Button>
      </div>
      {isLoading && (
        <div className="flex items-center justify-center py-2">
          <div className="w-5 h-5 border-t-2 border-b-2 border-blue-400 rounded-full animate-spin"></div>{" "}
          {/* 로딩 스피너 색상 변경 */}
        </div>
      )}
      <AGVSelectionInfo selectedAgvs={selectedAgvs} />
    </div>
  );
};

export default AGVControlPanel;
