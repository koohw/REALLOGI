import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/authApi';

const ModifyInfoForm = () => {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    newPasswordConfirm: '',
    userName: '',
    phoneNumber: ''
  });

  const [status, setStatus] = useState({
    loading: false,
    error: null,
    success: false
  });

  const navigate = useNavigate();

  useEffect(() => {
    loadUserInfo();
  }, []);

  const loadUserInfo = async () => {
    try {
      const response = await authApi.getCurrentUser();
      if (response.success && response.data) {
        setFormData(prev => ({
          ...prev,
          userName: response.data.userName || '',
          phoneNumber: response.data.phoneNumber || ''
        }));
      }
    } catch (error) {
      setStatus(prev => ({
        ...prev,
        error: '사용자 정보를 불러오는데 실패했습니다.'
      }));
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!formData.currentPassword) {
      setStatus(prev => ({ ...prev, error: '현재 비밀번호를 입력해주세요.' }));
      return false;
    }

    if (formData.newPassword && formData.newPassword !== formData.newPasswordConfirm) {
      setStatus(prev => ({ ...prev, error: '새 비밀번호가 일치하지 않습니다.' }));
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setStatus({ loading: true, error: null, success: false });

    try {
      const updateData = {
        currentPassword: formData.currentPassword,
        newPassword: formData.newPassword || undefined,
        userName: formData.userName || undefined,
        phoneNumber: formData.phoneNumber || undefined
      };

      const response = await authApi.updateUserInfo(updateData);
      
      if (response.success) {
        setStatus({ loading: false, error: null, success: true });
        setFormData({
          currentPassword: '',
          newPassword: '',
          newPasswordConfirm: '',
          userName: response.data.userName || '',
          phoneNumber: response.data.phoneNumber || ''
        });
        
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      } else {
        setStatus({ loading: false, error: response.message || '업데이트에 실패했습니다.', success: false });
      }
    } catch (error) {
      setStatus({ loading: false, error: error.message || '서버 오류가 발생했습니다.', success: false });
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">개인정보 수정</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label className="block text-gray-700 text-lg">현재 비밀번호</label>
          <input
            type="password"
            name="currentPassword"
            value={formData.currentPassword}
            onChange={handleChange}
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="현재 비밀번호 입력"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-gray-700 text-lg">새 비밀번호</label>
          <input
            type="password"
            name="newPassword"
            value={formData.newPassword}
            onChange={handleChange}
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="새 비밀번호 입력 (선택사항)"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-gray-700 text-lg">새 비밀번호 확인</label>
          <input
            type="password"
            name="newPasswordConfirm"
            value={formData.newPasswordConfirm}
            onChange={handleChange}
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="새 비밀번호 다시 입력"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-gray-700 text-lg">이름</label>
          <input
            type="text"
            name="userName"
            value={formData.userName}
            onChange={handleChange}
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="새로운 이름 입력 (선택사항)"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-gray-700 text-lg">전화번호</label>
          <input
            type="tel"
            name="phoneNumber"
            value={formData.phoneNumber}
            onChange={handleChange}
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="새로운 전화번호 입력 (선택사항)"
          />
        </div>

        {status.error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">{status.error}</p>
          </div>
        )}

        {status.success && (
          <div className="bg-green-50 border-l-4 border-green-500 p-4">
            <p className="text-green-700">정보가 성공적으로 업데이트되었습니다.</p>
          </div>
        )}

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={status.loading}
            className="flex-1 bg-gray-800 text-white p-3 rounded-md hover:bg-gray-700 transition-colors disabled:bg-gray-400"
          >
            {status.loading ? '처리중...' : '수정하기'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="flex-1 bg-gray-200 text-gray-800 p-3 rounded-md hover:bg-gray-300 transition-colors"
          >
            취소
          </button>
        </div>
      </form>
    </div>
  );
};

export default ModifyInfoForm;