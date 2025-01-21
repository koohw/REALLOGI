import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import * as Sentry from "@sentry/browser";
import reportWebVitals from "./reportWebVitals";

Sentry.init({
  dsn: "https://6267000ad124a20ca80db62454f94b16@o4508679586054144.ingest.us.sentry.io/4508679588610048",
  integrations: [],
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
