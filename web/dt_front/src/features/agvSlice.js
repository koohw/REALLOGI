import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  agvData: [],
  lastEfficiency: null,
  statusCounts: {
    operating: 0,
    waiting: 0,
    charging: 0,
    error: 0,
  },
  orderTotal: 0,
  agvs: [], // AGV 상세 정보를 위한 상태 추가
};

const agvSlice = createSlice({
  name: "agv",
  initialState,
  reducers: {
    updateAGVData: (state, action) => {
      const { timeLabel, efficiency } = action.payload;
      state.agvData = [...state.agvData, { time: timeLabel, efficiency }].slice(
        -10
      );
      state.lastEfficiency = efficiency;
    },
    updateStatusCounts: (state, action) => {
      state.statusCounts = action.payload;
    },
    updateOrderTotal: (state, action) => {
      state.orderTotal = action.payload;
    },
    updateAGVs: (state, action) => {
      state.agvs = action.payload;
    },
  },
});

export const { updateAGVData, updateStatusCounts, updateOrderTotal } =
  agvSlice.actions;
export default agvSlice.reducer;
