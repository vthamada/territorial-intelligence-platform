import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { Providers } from "./app/providers";
import { createAppRouter } from "./app/router";
import { bootstrapFrontendObservability } from "./shared/observability/bootstrap";
import "./styles/global.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Missing #root element");
}

bootstrapFrontendObservability();

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <Providers>
      <RouterProvider router={createAppRouter()} />
    </Providers>
  </React.StrictMode>
);
