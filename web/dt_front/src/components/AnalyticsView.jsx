import React, { useState, useEffect } from "react";
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

const AnalyticsView = ({ agvData }) => {
  const [efficiencyData, setEfficiencyData] = useState([]);
  const [quantityData, setQuantityData] = useState([]);
  const totalCapacity = 3000;
  const [lastEfficiency, setLastEfficiency] = useState(null);

  useEffect(() => {
    if (!agvData) return;

    // Update efficiency data only when it changes
    const currentEfficiency = agvData.overall_efficiency;
    if (lastEfficiency === null || currentEfficiency !== lastEfficiency) {
      const timestamp = new Date(agvData.overall_efficiency_history[0][0]);
      const timeLabel = `${String(timestamp.getHours()).padStart(
        2,
        "0"
      )}:${String(timestamp.getMinutes()).padStart(2, "0")}:${String(
        timestamp.getSeconds()
      ).padStart(2, "0")}`;

      setEfficiencyData((prev) => {
        const newData = [
          ...prev.slice(-9),
          { time: timeLabel, efficiency: currentEfficiency },
        ];
        return newData;
      });
      setLastEfficiency(currentEfficiency);
    }

    // Calculate total completed orders
    const completedOrders = Object.values(agvData.order_success).reduce(
      (sum, count) => sum + count,
      0
    );
    const remainingOrders = totalCapacity - completedOrders;

    setQuantityData([
      {
        name: "잔여",
        value: remainingOrders,
        remaining: remainingOrders,
        completed: 0,
      },
      {
        name: "완료",
        value: completedOrders,
        remaining: 0,
        completed: completedOrders,
      },
    ]);
  }, [agvData, lastEfficiency]);

  return (
    <div className="space-y-6 p-4 bg-gray-900 rounded-lg">
      {/* Efficiency Graph */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">실시간 AGV 효율성</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={efficiencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tick={{ fill: "#9CA3AF" }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis
                domain={[0, 15]}
                ticks={[0, 5, 10, 15]}
                tick={{ fill: "#9CA3AF" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
                formatter={(value) => [`${value.toFixed(2)}%`, "효율성"]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="efficiency"
                name="효율성"
                stroke="#60A5FA"
                strokeWidth={2}
                dot={true}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quantity Bar Chart */}
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
    </div>
  );
};

export default AnalyticsView;
