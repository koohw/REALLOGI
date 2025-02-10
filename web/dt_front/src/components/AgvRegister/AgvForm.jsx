import { useState ,useEffect} from 'react';
import axios from 'axios';
import { useAuth } from '../../hooks/useAuth';


export default function AgvForm({ onSubmit }) {

  const { user } = useAuth();
  const [formData, setFormData] = useState({
    agvName: '',
    agvCode: '',
    agvModel: '',
    agvFootnote: '',
    warehouseId: ''
  });

  const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8080';
  const fullUrl = `${baseUrl}/Agvs/register`;
  

  useEffect(() => {
    // user 정보가 있을 때 warehouseId 설정
    if (user && user.warehouseId) {
      setFormData(prev => ({
        ...prev,
        warehouseId: user.warehouseId
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
      const response = await axios.post(fullUrl, 
        {
          ...formData,
          warehouseId: parseInt(formData.warehouseId)
        },
        {
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      if (response.data.isSuccess) {
        alert('AGV가 성공적으로 등록되었습니다.');
        // 폼 초기화
        setFormData({
          agvName: '',
  agvCode: '',
  agvModel: '',
  agvFootnote: '',
          warehouseId: formData.warehouseId
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
          name="agvName"
          value={formData.agvName}
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
          name="agvCode"
          value={formData.agvCode}
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
           name="agvModel"
           value={formData.agvModel}
           onChange={handleChange}
           className="w-full p-2 border rounded-lg"
           placeholder="AGV 모델명"
           required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">비고</label>
        <textarea
          name="agvFootnote"
          value={formData.agvFootnote}
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