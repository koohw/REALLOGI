import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  updateAGVData,
  updateStatusCounts,
  updateOrderTotal,
  updateOrderSuccess,
} from "../features/agvSlice";
import { agvService } from "../api/agvService";

const AnalyticsView = () => {
  const dispatch = useDispatch();
  // Redux에 저장된 데이터들을 가져옵니다.
  const agvData = useSelector((state) => state.agv.agvData);
  const lastEfficiency = useSelector((state) => state.agv.lastEfficiency);
  const orderSuccessTotal = useSelector((state) => state.agv.orderTotal);
  const orderSuccessByAGV = useSelector((state) => state.agv.order_success);

  // SSE 구독: 효율성 값이 변할 때만 updateAGVData 액션을 디스패치합니다.
  useEffect(() => {
    const eventSource = agvService.getAgvStream();

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // 상태 카운트 업데이트
      const statusCounts = {
        operating: data.agv_number,
        waiting: data.agvs.filter((agv) => agv.state === "STOPPED").length,
        charging: data.agvs.filter((agv) => agv.state === "LOADING").length,
        error: data.agvs.filter((agv) => agv.issue !== "").length,
      };
      dispatch(updateStatusCounts(statusCounts));

      // 주문 총합 업데이트 및 AGV별 주문 성공 데이터 업데이트
      const orderTotal = Object.values(data.order_success).reduce(
        (sum, count) => sum + count,
        0
      );
      dispatch(updateOrderTotal(orderTotal));
      dispatch(updateOrderSuccess(data.order_success));

      // 효율성 데이터 업데이트: 값이 변경되었을 때만 추가
      const currentEfficiency = data.overall_efficiency;
      if (lastEfficiency === null || currentEfficiency !== lastEfficiency) {
        // overall_efficiency_history 배열의 첫 번째 타임스탬프 사용
        const timestamp = new Date(data.overall_efficiency_history[0][0]);
        const timeLabel = `${String(timestamp.getHours()).padStart(
          2,
          "0"
        )}:${String(timestamp.getMinutes()).padStart(2, "0")}:${String(
          timestamp.getSeconds()
        ).padStart(2, "0")}`;

        dispatch(updateAGVData({ timeLabel, efficiency: currentEfficiency }));
      }
    };

    // eventSource.onerror = (error) => {
    //   console.error("SSE Error:", error);
    //   eventSource.close();
    // };

    return () => {
      eventSource.close();
    };
  }, [dispatch, lastEfficiency]);

  // 여기서는 Redux에 저장된 전체 agvData를 그대로 사용합니다.
  // (SSE에서 값이 갱신될 때만 데이터가 추가되므로, 그래프에는 변경된 값만 나타납니다.)
  const efficiencyData = agvData;

  // 물동량 차트 데이터 준비
  const totalCapacity = 3000;
  const quantityData = [
    { name: "잔여", remaining: totalCapacity - orderSuccessTotal },
    { name: "완료", completed: orderSuccessTotal },
  ];

  // AGV 주문 성공 차트 데이터 준비
  const agvOrderSuccessData = Object.entries(orderSuccessByAGV || {}).map(
    ([agv, success]) => ({ agv, success })
  );

  return (
    <div className="space-y-4 p-4 bg-gray-900 rounded-lg">
      {/* 실시간 AGV 효율성 그래프 */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">실시간 AGV 효율성</h3>
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={efficiencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
              <XAxis
                dataKey="time"
                padding={{ left: 30, right: 30 }}
                angle={-45}
                textAnchor="end"
                height={60}
                tick={{ fill: "#fff" }}
              />
              <YAxis
                domain={[0, 30]}
                ticks={[0, 15, 30]}
                tick={{ fill: "#fff" }}
                label={{
                  value: "효율성",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#fff",
                  style: { textAnchor: "middle" },
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#11263f",
                  border: "none",
                  color: "white",
                  borderRadius: "4px",
                }}
                labelStyle={{ color: "white" }}
                formatter={(value) => `${value.toFixed(2)}sec`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="efficiency"
                name="AGV 효율성"
                stroke="#fff"
                strokeWidth={2}
                dot={true}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 물동량 바 차트 */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">물동량 현황</h3>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={quantityData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" tick={{ fill: "#9CA3AF" }} />
              <YAxis
                dataKey="name"
                type="category"
                tick={{ fill: "#9CA3AF" }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
              />
              <Legend />
              <Bar
                dataKey="remaining"
                name="잔여"
                fill="#EF4444"
                radius={[0, 4, 4, 0]}
                stackId="a"
              />
              <Bar
                dataKey="completed"
                name="완료"
                fill="#10B981"
                radius={[0, 4, 4, 0]}
                stackId="a"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AGV 별 주문 성공 바 차트 */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">AGV 별 주문 성공</h3>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={agvOrderSuccessData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="agv" tick={{ fill: "#9CA3AF" }} />
              <YAxis tick={{ fill: "#9CA3AF" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
              />
              <Legend />
              <Bar dataKey="success" name="주문 성공" fill="#FBBF24" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsView;
