const BASE_URL = "http://localhost:8080/api/users";

export const authApi = {
  login: async (email, password) => {
    try {
      const response = await fetch(`${BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      return await response.json();
    } catch (error) {
      throw new Error("Login failed");
    }
  },

  logout: async () => {
    try {
      const response = await fetch(`${BASE_URL}/logout`, {
        method: "POST",
        credentials: "include",
      });
      return await response.json();
    } catch (error) {
      throw new Error("Logout failed");
    }
  },

  getCurrentUser: async () => {
    try {
      const response = await fetch(`${BASE_URL}/current`, {
        credentials: "include",
      });
      return await response.json();
    } catch (error) {
      throw new Error("Failed to get current user");
    }
  },
  checkEmail: async (email) => {
    try {
      const response = await fetch(`${BASE_URL}/check-email?email=${email}`, {
        credentials: "include",
      });
      return await response.json();
    } catch (error) {
      throw new Error("Email check failed");
    }
  },

  signup: async (userData) => {
    try {
      const response = await fetch(`${BASE_URL}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(userData),
      });
      return await response.json();
    } catch (error) {
      throw new Error("Signup failed");
    }
  },

  getCompanies: async () => {
    try {
      const response = await fetch("http://localhost:8080/api/companies", {
        credentials: "include",
      });
      return await response.json();
    } catch (error) {
      throw new Error("Failed to fetch companies");
    }
  },

  getWarehouses: async (companyId) => {
    try {
      const response = await fetch(`${BASE_URL}/warehouses/${companyId}`, {
        credentials: "include",
      });
      return await response.json();
    } catch (error) {
      throw new Error("Failed to fetch warehouses");
    }
  },
};
