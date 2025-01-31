export default function SimulationForm({ onSubmit }) {
    const handleSubmit = (e) => {
      e.preventDefault();
      const formData = {
        설정_물동량: e.target.물동량.value,
        설정_AGV대수: e.target.agv대수.value,
      };
      onSubmit(formData);
    };
  
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">시뮬레이션 설정</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">설정 물동량</label>
            <input
              type="text"
              name="물동량"
              className="w-full p-2 border rounded-lg"
              placeholder="물동량 입력"
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium">설정 AGV 대수</label>
            <input
              type="text"
              name="agv대수"
              className="w-full p-2 border rounded-lg"
              placeholder="AGV 대수 입력"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-black text-white py-2 rounded-lg hover:bg-gray-800"
          >
            설정
          </button>
        </form>
      </div>
    );
  }