// components/AGVControlPanel.jsx
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
    <div className="p-4 space-y-4 bg-white rounded-lg shadow">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">AGV 제어 패널</h3>
        {selectedAgvs.length > 0 && (
          <button
            onClick={onActionComplete}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center"
          >
            <X className="w-4 h-4 mr-1" />
            선택 해제
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 mb-4 text-sm text-red-700 bg-red-100 rounded-md">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={() => handleAction("stop")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1"
        >
          <Pause className="w-4 h-4 mr-2" />
          정지
        </Button>
        <Button
          variant="secondary"
          onClick={() => handleAction("return")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          복귀
        </Button>
        <Button
          variant="secondary"
          onClick={() => handleAction("restart")}
          disabled={isLoading || selectedAgvs.length === 0}
          className="flex-1"
        >
          <Play className="w-4 h-4 mr-2" />
          재가동
        </Button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-2">
          <div className="w-5 h-5 border-t-2 border-b-2 border-blue-500 rounded-full animate-spin"></div>
        </div>
      )}

      <AGVSelectionInfo selectedAgvs={selectedAgvs} />
    </div>
  );
};

export default AGVControlPanel;
