import { useState } from "react";
import AgvForm from "./AgvForm";
import SuccessModal from "./SuccessModal";

export default function AgvRegister() {
  const [showModal, setShowModal] = useState(false);

  const handleSubmit = async (formData) => {
    try {
      const response = await fetch("/api/agv/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(true);
      }
    } catch (error) {
      console.error("AGV 등록 실패:", error);
    }
  };

  return (
    <div className="p-6 bg-[#11263f]">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold mb-6 text-gray-200">AGV 등록</h2>
        <AgvForm onSubmit={handleSubmit} />
      </div>
      <SuccessModal show={showModal} onClose={() => setShowModal(false)} />
    </div>
  );
}
