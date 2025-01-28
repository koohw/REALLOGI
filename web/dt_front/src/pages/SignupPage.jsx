import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/authApi";

const SignupPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    passwordConfirm: "",
    userName: "",
    phoneNumber: "",
    companyId: "",
    warehouseId: "",
    warehouseCode: "",
  });

  const [companies, setCompanies] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [errors, setErrors] = useState({});
  const [isEmailAvailable, setIsEmailAvailable] = useState(null);

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      const response = await authApi.getCompanies();
      if (response.success) {
        setCompanies(response.data);
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: "회사 목록을 불러오는데 실패했습니다.",
      }));
    }
  };

  const loadWarehouses = async (companyId) => {
    try {
      const response = await authApi.getWarehouses(companyId);
      if (response.success) {
        setWarehouses(response.data);
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: "창고 목록을 불러오는데 실패했습니다.",
      }));
    }
  };

  const handleChange = async (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (name === "companyId" && value) {
      setFormData((prev) => ({ ...prev, warehouseId: "", warehouseCode: "" }));
      loadWarehouses(value);
    }

    // Clear specific error when user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const checkEmail = async () => {
    if (!formData.email) return;

    try {
      const response = await authApi.checkEmail(formData.email);
      setIsEmailAvailable(!response.data);
      if (response.data) {
        setErrors((prev) => ({
          ...prev,
          email: "이미 사용 중인 이메일입니다.",
        }));
      } else {
        setErrors((prev) => ({ ...prev, email: "" }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        email: "이메일 중복 확인에 실패했습니다.",
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.email) newErrors.email = "이메일은 필수입니다.";
    if (!isEmailAvailable) newErrors.email = "이메일 중복 확인이 필요합니다.";
    if (!formData.password) newErrors.password = "비밀번호는 필수입니다.";
    if (formData.password !== formData.passwordConfirm) {
      newErrors.passwordConfirm = "비밀번호가 일치하지 않습니다.";
    }
    if (!formData.userName) newErrors.userName = "이름은 필수입니다.";
    if (!formData.companyId) newErrors.companyId = "회사 선택은 필수입니다.";
    if (!formData.warehouseId)
      newErrors.warehouseId = "창고 선택은 필수입니다.";
    if (!formData.warehouseCode)
      newErrors.warehouseCode = "창고 코드는 필수입니다.";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      const signupData = {
        ...formData,
        companyId: parseInt(formData.companyId),
        warehouseId: parseInt(formData.warehouseId),
      };
      delete signupData.passwordConfirm;

      const response = await authApi.signup(signupData);
      if (response.success) {
        alert("회원가입이 완료되었습니다.");
        navigate("/login");
      } else {
        setErrors((prev) => ({ ...prev, general: response.message }));
      }
    } catch (error) {
      setErrors((prev) => ({ ...prev, general: "회원가입에 실패했습니다." }));
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col justify-center items-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-4xl font-bold text-center mb-8">회원가입</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-gray-700 text-lg">이메일</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="이메일 입력"
                />
              </div>
              <button
                type="button"
                onClick={checkEmail}
                className="mt-8 px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-700"
              >
                중복확인
              </button>
            </div>
            {errors.email && (
              <p className="text-red-500 text-sm">{errors.email}</p>
            )}
            {isEmailAvailable && (
              <p className="text-green-500 text-sm">
                사용 가능한 이메일입니다.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">비밀번호</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="비밀번호 입력"
            />
            {errors.password && (
              <p className="text-red-500 text-sm">{errors.password}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">비밀번호 확인</label>
            <input
              type="password"
              name="passwordConfirm"
              value={formData.passwordConfirm}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="비밀번호 다시 입력"
            />
            {errors.passwordConfirm && (
              <p className="text-red-500 text-sm">{errors.passwordConfirm}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">이름</label>
            <input
              type="text"
              name="userName"
              value={formData.userName}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="이름 입력"
            />
            {errors.userName && (
              <p className="text-red-500 text-sm">{errors.userName}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">전화번호</label>
            <input
              type="tel"
              name="phoneNumber"
              value={formData.phoneNumber}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="전화번호 입력 (선택사항)"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">회사 선택</label>
            <select
              name="companyId"
              value={formData.companyId}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">회사를 선택하세요</option>
              {companies.map((company) => (
                <option key={company.companyId} value={company.companyId}>
                  {company.companyName}
                </option>
              ))}
            </select>
            {errors.companyId && (
              <p className="text-red-500 text-sm">{errors.companyId}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">창고 선택</label>
            <select
              name="warehouseId"
              value={formData.warehouseId}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={!formData.companyId}
            >
              <option value="">창고를 선택하세요</option>
              {warehouses.map((warehouse) => (
                <option
                  key={warehouse.warehouseId}
                  value={warehouse.warehouseId}
                >
                  {warehouse.warehouseName}
                </option>
              ))}
            </select>
            {errors.warehouseId && (
              <p className="text-red-500 text-sm">{errors.warehouseId}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="block text-gray-700 text-lg">창고 코드</label>
            <input
              type="text"
              name="warehouseCode"
              value={formData.warehouseCode}
              onChange={handleChange}
              className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="창고 코드 입력"
            />
            {errors.warehouseCode && (
              <p className="text-red-500 text-sm">{errors.warehouseCode}</p>
            )}
          </div>

          {errors.general && (
            <div className="text-red-500 text-sm text-center">
              {errors.general}
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-gray-800 text-white p-3 rounded-md hover:bg-gray-700 transition-colors"
          >
            가입하기
          </button>

          <div className="text-center">
            <a href="/login" className="text-gray-600 hover:text-gray-800">
              이미 계정이 있으신가요? 로그인하기
            </a>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SignupPage;
