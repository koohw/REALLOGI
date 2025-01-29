import { useState } from 'react';
import SimulationForm from './SimulationForm';
import SimulationGraph from './SimulationGraph';
import SimulationResult from './SimulationResult';

export default function Simulation() {
  const [simulationData, setSimulationData] = useState(null);

  const handleSimulation = async (formData) => {
    // 시뮬레이터 API 호출 로직 구현 예정
    console.log('시뮬레이션 데이터:', formData);
  };

  return (
    <div className="p-6 space-y-6">
     <div className="grid grid-cols-3 gap-6">
        <div className="w-full">
          <SimulationForm onSubmit={handleSimulation} />
        </div>
        <div className="col-span-2">
          <SimulationGraph />
        </div>
      </div>
      
      <div className="w-full">
        <SimulationResult />
      </div>
    </div>
  );
}