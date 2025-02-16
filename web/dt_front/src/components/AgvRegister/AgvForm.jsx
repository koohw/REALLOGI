import { useState, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { agvApi } from "../../api/agvApi";



export default function AgvForm({ onSubmit }) {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    agvName: "",
    agvCode: "",
    agvModel: "",
    agvFootnote: "",
    warehouseId: "",
  });
  
  

  useEffect(() => {
    // user 정보가 있을 때 warehouseId 설정
    if (user && user.warehouseId) {
      setFormData((prev) => ({
        ...prev,
        warehouseId: user.warehouseId,
      }));
    }
  }, [user]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await agvApi.registerAgv({
        ...formData,
        warehouseId: parseInt(formData.warehouseId)
      });
      if (response.isSuccess) {
        alert("AGV가 성공적으로 등록되었습니다.");
        // 폼 초기화
        setFormData({
          agvName: "",
          agvCode: "",
          agvModel: "",
          agvFootnote: "",
          warehouseId: formData.warehouseId,
        });
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error("Error:", error);
      alert("AGV 등록에 실패했습니다.");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 bg-[#11263f] p-6 rounded-lg shadow-lg border border-gray-700"
    >
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Name</label>
        <input
          type="text"
          name="agvName"
          value={formData.agvName}
          onChange={handleChange}
          className="w-full p-2 border border-gray-600 rounded-lg bg-[#0D1B2A] text-gray-200 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="Agv 이름"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Code</label>
        <input
          type="text"
          name="agvCode"
          value={formData.agvCode}
          onChange={handleChange}
          className="w-full p-2 border border-gray-600 rounded-lg bg-[#0D1B2A] text-gray-200 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="AGV 코드"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Model</label>
        <input
          type="text"
          name="agvModel"
          value={formData.agvModel}
          onChange={handleChange}
          className="w-full p-2 border border-gray-600 rounded-lg bg-[#0D1B2A] text-gray-200 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="AGV 모델명"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">비고</label>
        <textarea
          name="agvFootnote"
          value={formData.agvFootnote}
          onChange={handleChange}
          className="w-full p-2 border border-gray-600 rounded-lg bg-[#0D1B2A] text-gray-200 h-32
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="비고"
          required
        />
      </div>

      <button
        type="submit"
        className="w-full bg-blue-900 text-gray-200 py-3 rounded-lg hover:bg-blue-800 
                 transition-colors border border-gray-600"
      >
        AGV 등록
      </button>
    </form>
  );
}
