import { createBrowserRouter } from "react-router-dom";
import { App } from "./App";
import { OpsHealthPage } from "../modules/ops/pages/OpsHealthPage";
import { OpsRunsPage } from "../modules/ops/pages/OpsRunsPage";
import { TerritoryIndicatorsPage } from "../modules/territory/pages/TerritoryIndicatorsPage";

export function createAppRouter() {
  return createBrowserRouter([
    {
      path: "/",
      element: <App />,
      children: [
        { index: true, element: <OpsHealthPage /> },
        { path: "ops/runs", element: <OpsRunsPage /> },
        { path: "territory/indicators", element: <TerritoryIndicatorsPage /> }
      ]
    }
  ]);
}
