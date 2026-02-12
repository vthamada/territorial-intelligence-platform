import { Suspense, lazy, type ReactNode } from "react";
import { createBrowserRouter, createMemoryRouter, type RouteObject } from "react-router-dom";
import { App } from "./App";
import { RouteErrorPage } from "./RouteErrorPage";

const routerFutureFlags = {
  v7_startTransition: true,
  v7_relativeSplatPath: true
} as const;

const OpsHealthPage = lazy(() =>
  import("../modules/ops/pages/OpsHealthPage").then((mod) => ({ default: mod.OpsHealthPage }))
);
const QgOverviewPage = lazy(() =>
  import("../modules/qg/pages/QgOverviewPage").then((mod) => ({ default: mod.QgOverviewPage }))
);
const QgPrioritiesPage = lazy(() =>
  import("../modules/qg/pages/QgPrioritiesPage").then((mod) => ({ default: mod.QgPrioritiesPage }))
);
const QgMapPage = lazy(() =>
  import("../modules/qg/pages/QgMapPage").then((mod) => ({ default: mod.QgMapPage }))
);
const QgInsightsPage = lazy(() =>
  import("../modules/qg/pages/QgInsightsPage").then((mod) => ({ default: mod.QgInsightsPage }))
);
const QgScenariosPage = lazy(() =>
  import("../modules/qg/pages/QgScenariosPage").then((mod) => ({ default: mod.QgScenariosPage }))
);
const QgBriefsPage = lazy(() =>
  import("../modules/qg/pages/QgBriefsPage").then((mod) => ({ default: mod.QgBriefsPage }))
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
const OpsFrontendEventsPage = lazy(() =>
  import("../modules/ops/pages/OpsFrontendEventsPage").then((mod) => ({ default: mod.OpsFrontendEventsPage }))
);
const OpsSourceCoveragePage = lazy(() =>
  import("../modules/ops/pages/OpsSourceCoveragePage").then((mod) => ({ default: mod.OpsSourceCoveragePage }))
);
const AdminHubPage = lazy(() =>
  import("../modules/admin/pages/AdminHubPage").then((mod) => ({ default: mod.AdminHubPage }))
);
const TerritoryIndicatorsPage = lazy(() =>
  import("../modules/territory/pages/TerritoryIndicatorsPage").then((mod) => ({ default: mod.TerritoryIndicatorsPage }))
);
const TerritoryProfilePage = lazy(() =>
  import("../modules/territory/pages/TerritoryProfilePage").then((mod) => ({ default: mod.TerritoryProfilePage }))
);
const TerritoryProfileRoutePage = lazy(() =>
  import("../modules/territory/pages/TerritoryProfileRoutePage").then((mod) => ({ default: mod.TerritoryProfileRoutePage }))
);
const ElectorateExecutivePage = lazy(() =>
  import("../modules/electorate/pages/ElectorateExecutivePage").then((mod) => ({ default: mod.ElectorateExecutivePage }))
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
    errorElement: (
      <App>
        <RouteErrorPage />
      </App>
    ),
    children: [
      { index: true, element: withPageFallback(<QgOverviewPage />) },
      { path: "prioridades", element: withPageFallback(<QgPrioritiesPage />) },
      { path: "mapa", element: withPageFallback(<QgMapPage />) },
      { path: "insights", element: withPageFallback(<QgInsightsPage />) },
      { path: "cenarios", element: withPageFallback(<QgScenariosPage />) },
      { path: "briefs", element: withPageFallback(<QgBriefsPage />) },
      { path: "admin", element: withPageFallback(<AdminHubPage />) },
      { path: "ops/health", element: withPageFallback(<OpsHealthPage />) },
      { path: "ops/runs", element: withPageFallback(<OpsRunsPage />) },
      { path: "ops/checks", element: withPageFallback(<OpsChecksPage />) },
      { path: "ops/connectors", element: withPageFallback(<OpsConnectorsPage />) },
      { path: "ops/frontend-events", element: withPageFallback(<OpsFrontendEventsPage />) },
      { path: "ops/source-coverage", element: withPageFallback(<OpsSourceCoveragePage />) },
      { path: "territory/indicators", element: withPageFallback(<TerritoryIndicatorsPage />) },
      { path: "territorio/perfil", element: withPageFallback(<TerritoryProfilePage />) },
      { path: "territorio/:territoryId", element: withPageFallback(<TerritoryProfileRoutePage />) },
      { path: "territory/profile", element: withPageFallback(<TerritoryProfilePage />) },
      { path: "territory/:territoryId", element: withPageFallback(<TerritoryProfileRoutePage />) },
      { path: "eleitorado", element: withPageFallback(<ElectorateExecutivePage />) },
      { path: "electorate/executive", element: withPageFallback(<ElectorateExecutivePage />) }
    ]
  }
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes, { future: routerFutureFlags });
}

export function createAppMemoryRouter(initialEntries: string[] = ["/"]) {
  return createMemoryRouter(appRoutes, { initialEntries, future: routerFutureFlags });
}
