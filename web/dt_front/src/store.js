// src/store.js
import { configureStore } from "@reduxjs/toolkit";
import userReducer from "./features/userSlice";

const store = configureStore({
  reducer: {
    user: userReducer, // user slice를 리듀서로 사용
  },
});

export default store;
