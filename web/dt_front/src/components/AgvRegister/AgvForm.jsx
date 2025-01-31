import { useState } from 'react';

export default function AgvForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    registrationId: '',
    description: '',
    isConnected: false
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow">
      <div className="space-y-2">
        <label className="block text-sm font-medium">Name</label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg"
          placeholder="Value"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">ID</label>
        <input
          type="text"
          name="registrationId"
          value={formData.registrationId}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg"
          placeholder="Value"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">Connect</label>
        <div className={`p-2 rounded-lg ${
          formData.isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {formData.isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium">Description</label>
        <textarea
          name="description"
          value={formData.description}
          onChange={handleChange}
          className="w-full p-2 border rounded-lg h-32"
          placeholder="Value"
          required
        />
      </div>

      <button
        type="submit"
        className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors"
      >
        Submit
      </button>
    </form>
  );
}