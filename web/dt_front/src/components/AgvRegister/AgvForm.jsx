import { useState ,useEffect} from 'react';
import axios from 'axios';

export default function AgvForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    agv_name: '',
    agv_code: '',
    agv_model: '',
    footnote: '',
    warehouseId : ''
  });
  

  useEffect(() => {
    // localStorage에서 warehouse_id 가져오기
    const warehouse_id = localStorage.getItem('warehouse_id');
    if (warehouse_id) {
      setFormData(prev => ({
        ...prev,
        warehouse_id: parseInt(warehouse_id)
      }));
    }
  }, []);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:8080/api/Agvs/register', formData);
      if (response.data.isSuccess) {
        alert('AGV가 성공적으로 등록되었습니다.');
        // 폼 초기화
        setFormData({
          agv_name: '',
          agv_code: '',
          agv_model: '',
          footnote: '',
          warehouse_id: formData.warehouse_id
        });
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('AGV 등록에 실패했습니다.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow">
      <div className="space-y-2">
        <label className="block text-sm font-medium">Name</label>
        <input
          type="text"
          name="agv_name"
          value={formData.agv_name}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg"
          placeholder="Agv 이름"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">code</label>
        <input
          type="text"
          name="agv_code"
          value={formData.agv_code}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg"
          placeholder="AGV 코드"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">Model</label>
        <input
           type="text"
           name="agv_model"
           value={formData.agv_model}
           onChange={handleChange}
           className="w-full p-2 border rounded-lg"
           placeholder="AGV 모델명"
           required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">비고</label>
        <textarea
          name="footnote"
          value={formData.footnote}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg h-32"
          placeholder="비고"
          required
        />
      </div>

      <button
        type="submit"
        className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors"
      >
        AGV 등록
      </button>
    </form>
  );
}