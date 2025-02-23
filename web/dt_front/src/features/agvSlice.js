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
  order_success: {}, // 추가: AGV별 주문 성공 데이터를 저장합니다.
  agvs: [],
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
    updateOrderSuccess: (state, action) => {
      state.order_success = action.payload;
    },
    updateAGVs: (state, action) => {
      state.agvs = action.payload;
    },
  },
});

export const {
  updateAGVData,
  updateStatusCounts,
  updateOrderTotal,
  updateOrderSuccess,
  updateAGVs,
} = agvSlice.actions;
export default agvSlice.reducer;
