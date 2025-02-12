import React, { useState, useEffect } from "react";
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

const RealTimeAGVGraph = ({ onDataUpdate, onOrderUpdate }) => {
  const [agvData, setAgvData] = useState([]);
  const [timeLabels, setTimeLabels] = useState([]);

  useEffect(() => {
    const eventSource = new EventSource("http://localhost:5000/api/agv-stream");

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Get current timestamp
      const now = new Date();
      const timeLabel = `${String(now.getHours()).padStart(2, "0")}:${String(
        now.getMinutes()
      ).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

      // Calculate status counts
      const statusCounts = {
        operating: data.agv_number,
        waiting: data.agvs.filter((agv) => agv.state === "STOPPED").length,
        charging: data.agvs.filter((agv) => agv.state === "UNLOADING").length,
        error: data.agvs.filter((agv) => agv.issue !== "").length,
      };

      // Calculate total order success
      const orderTotal = Object.values(data.order_success).reduce(
        (sum, count) => sum + count,
        0
      );
      const productCount = {
        total: orderTotal,
      };

      // Pass data to parent components
      if (onDataUpdate) {
        onDataUpdate(statusCounts);
      }
      if (onOrderUpdate) {
        onOrderUpdate({ productCount });
      }

      // Calculate efficiency metrics for graph
      const runningAgvs = data.agvs.filter(
        (agv) => agv.state === "RUNNING"
      ).length;
      const totalActiveAgvs = data.agvs.filter(
        (agv) => agv.state !== ""
      ).length;
      const efficiency =
        totalActiveAgvs > 0 ? (runningAgvs / totalActiveAgvs) * 100 : 0;

      // Update data (keep last 10 points)
      setTimeLabels((prev) => {
        const newLabels = [...prev, timeLabel];
        return newLabels.slice(-10);
      });

      setAgvData((prev) => {
        const newData = [
          ...prev,
          {
            time: timeLabel,
            efficiency: efficiency,
          },
        ];
        return newData.slice(-10);
      });
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [onDataUpdate, onOrderUpdate]);

  return (
    <div className="w-full bg-white rounded-lg p-4">
      <h2 className="text-lg font-semibold mb-4">실시간 AGV 효율성 그래프</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={agvData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              padding={{ left: 30, right: 30 }}
              angle={-45}
              textAnchor="end"
              height={60}
              interval={0}
            />
            <YAxis
              domain={[0, 100]}
              label={{
                value: "효율성 (%)",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="efficiency"
              name="AGV 효율성"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default RealTimeAGVGraph;
