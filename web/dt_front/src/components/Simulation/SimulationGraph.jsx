import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
  } from 'chart.js';
  import { Line } from 'react-chartjs-2';

export default function SimulationGraph() {
  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
        },
      }
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };

    //임시 데이터 
  const data = {
    labels: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
    datasets: [
      {
        label: '변경 전',
        data: [65, 70, 75, 80, 85, 90, 85, 80, 85, 90],
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      },
      {
        label: '변경 후',
        data: [60, 65, 70, 75, 80, 85, 80, 75, 80, 85],
        borderColor: 'rgb(153, 102, 255)',
        tension: 0.1
      }
    ]
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="h-80">
        <Line options={options} data={data} />
      </div>
      <div className="text-right mt-2 text-sm text-gray-500">
        A: 변경 전 / B: 변경 후
      </div>
    </div>
  );
}