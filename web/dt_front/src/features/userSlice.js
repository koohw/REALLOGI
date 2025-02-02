import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  user: null,
  isAuthenticated: false,
};

const userSlice = createSlice({
  name: "user",
  initialState,
  reducers: {
    login: (state, action) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
    logout: (state) => {
      state.user = null;
      state.isAuthenticated = false;
    },
    rehydrate: (state, action) => {
      state.user = action.payload?.user || null;
      state.isAuthenticated = !!action.payload?.user;
    },
  },
});

export const { login, logout, rehydrate } = userSlice.actions;
export default userSlice.reducer;
