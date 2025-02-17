import React, { useMemo } from "react";
import { useSelector } from "react-redux";
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

const AnalyticsView = () => {
  const efficiencyData = useSelector((state) => state.agv.agvData);
  const orderSuccess = useSelector((state) => state.agv.orderTotal);
  const totalCapacity = 3000;

  // Optimize efficiency data to only include points where values change
  const optimizedEfficiencyData = useMemo(() => {
    if (!efficiencyData || efficiencyData.length === 0) return [];

    return efficiencyData.reduce((acc, current, index) => {
      // Always include the first point
      if (index === 0) {
        return [current];
      }

      // Compare with the last point in our accumulated array
      const lastPoint = acc[acc.length - 1];

      // Include point if efficiency value is different from the last point
      if (Math.abs(lastPoint.efficiency - current.efficiency) > 0.01) {
        return [...acc, current];
      }

      // If it's the last point, always include it to ensure we have the latest state
      if (
        index === efficiencyData.length - 1 &&
        lastPoint.time !== current.time
      ) {
        return [...acc, current];
      }

      return acc;
    }, []);
  }, [efficiencyData]);

  // Calculate quantity data
  const quantityData = [
    {
      name: "잔여",
      remaining: totalCapacity - orderSuccess,
      completed: 0,
    },
    {
      name: "완료",
      remaining: 0,
      completed: orderSuccess,
    },
  ];

  return (
    <div className="space-y-6 p-4 bg-gray-900 rounded-lg">
      {/* Efficiency Graph */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">실시간 AGV 효율성</h3>
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={optimizedEfficiencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tick={{ fill: "#9CA3AF" }}
                angle={-45}
                textAnchor="end"
                height={60}
                interval={0}
              />
              <YAxis
                domain={[0, 30]}
                ticks={[0, 10, 20, 30]}
                tick={{ fill: "#9CA3AF" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
                formatter={(value) => [`${value.toFixed(2)}sec`, "효율성"]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="efficiency"
                name="효율성"
                stroke="#60A5FA"
                strokeWidth={2}
                dot={true}
                activeDot={{ r: 6 }}
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
