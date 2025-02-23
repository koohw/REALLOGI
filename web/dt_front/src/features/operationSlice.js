// src/store/operationSlice.js
import { createSlice } from "@reduxjs/toolkit";

const operationSlice = createSlice({
  name: "operation",
  initialState: { operationStarted: false },
  reducers: {
    startOperation(state) {
      state.operationStarted = true;
    },
    initializeOperation(state) {
      state.operationStarted = false;
    },
  },
});

export const { startOperation, initializeOperation } = operationSlice.actions;
export default operationSlice.reducer;
