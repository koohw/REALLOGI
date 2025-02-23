import { configureStore } from "@reduxjs/toolkit";
import { persistStore, persistReducer } from "redux-persist";
import storage from "redux-persist/lib/storage"; // localStorage 사용
import userReducer from "./features/userSlice";
import agvReducer from "./features/agvSlice";
import operationReducer from "./features/operationSlice";

const persistConfig = {
  key: "user",
  storage, // localStorage에 저장
};

const persistedReducer = persistReducer(persistConfig, userReducer);

const store = configureStore({
  reducer: {
    user: persistedReducer,
    agv: agvReducer,
    operation: operationReducer,
  },
});

export const persistor = persistStore(store);
export default store;
