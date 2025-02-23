import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import {
  LineChart,
  Line,
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
} from "../../features/agvSlice";

import { agvService } from "../../api/agvService";

const RealTimeAGVGraph = ({ onDataUpdate, onOrderUpdate }) => {
  const dispatch = useDispatch();
  const agvData = useSelector((state) => state.agv.agvData);
  const lastEfficiency = useSelector((state) => state.agv.lastEfficiency);

  
  useEffect(() => {
    const eventSource = agvService.getAgvStream();

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Update status counts
      const statusCounts = {
        operating: data.agv_number,
        waiting: data.agvs.filter((agv) => agv.state === "STOPPED").length,
        charging: data.agvs.filter((agv) => agv.state === "LOADING").length,
        error: data.agvs.filter((agv) => agv.issue !== "").length,
      };
      dispatch(updateStatusCounts(statusCounts));
      if (onDataUpdate) {
        onDataUpdate(statusCounts);
      }

      // Update order total
      const orderTotal = Object.values(data.order_success).reduce(
        (sum, count) => sum + count,
        0
      );
      dispatch(updateOrderTotal(orderTotal));
      if (onOrderUpdate) {
        onOrderUpdate({ productCount: { total: orderTotal } });
      }

      // Update efficiency data
      const currentEfficiency = data.overall_efficiency;
      if (lastEfficiency === null || currentEfficiency !== lastEfficiency) {
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

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [dispatch, lastEfficiency, onDataUpdate, onOrderUpdate]);

  return (
    <div className="w-full bg-[#0D1B2A] rounded-lg shadow-lg p-4 border border-white/10">
      <h2 className="text-lg font-semibold mb-4 text-white">
        실시간 AGV 효율성 그래프
      </h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={agvData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
            <XAxis
              dataKey="time"
              padding={{ left: 30, right: 30 }}
              angle={-45}
              textAnchor="end"
              height={60}
              interval={0}
              tick={{ fill: "#fff" }}
            />
            <YAxis
              domain={[0, 30]}
              ticks={[0, 10, 20, 30]}
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
              itemStyle={{ color: "white" }}
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
  );
};

export default RealTimeAGVGraph;
