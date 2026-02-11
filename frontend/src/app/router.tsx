import { Suspense, lazy, type ReactNode } from "react";
import { createBrowserRouter, createMemoryRouter, type RouteObject } from "react-router-dom";
import { App } from "./App";

const OpsHealthPage = lazy(() =>
  import("../modules/ops/pages/OpsHealthPage").then((mod) => ({ default: mod.OpsHealthPage }))
);
const OpsRunsPage = lazy(() =>
  import("../modules/ops/pages/OpsRunsPage").then((mod) => ({ default: mod.OpsRunsPage }))
);
const OpsChecksPage = lazy(() =>
  import("../modules/ops/pages/OpsChecksPage").then((mod) => ({ default: mod.OpsChecksPage }))
);
const OpsConnectorsPage = lazy(() =>
  import("../modules/ops/pages/OpsConnectorsPage").then((mod) => ({ default: mod.OpsConnectorsPage }))
);
const TerritoryIndicatorsPage = lazy(() =>
  import("../modules/territory/pages/TerritoryIndicatorsPage").then((mod) => ({ default: mod.TerritoryIndicatorsPage }))
);

function withPageFallback(element: ReactNode) {
  return (
    <Suspense fallback={<div className="state-block state-loading">Carregando pagina...</div>}>
      {element}
    </Suspense>
  );
}

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: withPageFallback(<OpsHealthPage />) },
      { path: "ops/runs", element: withPageFallback(<OpsRunsPage />) },
      { path: "ops/checks", element: withPageFallback(<OpsChecksPage />) },
      { path: "ops/connectors", element: withPageFallback(<OpsConnectorsPage />) },
      { path: "territory/indicators", element: withPageFallback(<TerritoryIndicatorsPage />) }
    ]
  }
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}

export function createAppMemoryRouter(initialEntries: string[] = ["/"]) {
  return createMemoryRouter(appRoutes, { initialEntries });
}
