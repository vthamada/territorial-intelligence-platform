import { useEffect, useRef, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { emitTelemetry } from "../shared/observability/telemetry";
import { NavIcon } from "../shared/ui/NavIcon";

type AppProps = {
  children?: ReactNode;
};

export function App({ children }: AppProps) {
  const location = useLocation();
  const previousPathRef = useRef<string | null>(null);
  const mainContentRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const currentPath = `${location.pathname}${location.search}`;
    const previousPath = previousPathRef.current;
    previousPathRef.current = currentPath;

    emitTelemetry({
      category: "lifecycle",
      name: "route_change",
      severity: "info",
      attributes: {
        from: previousPath,
        to: currentPath
      }
    });

    mainContentRef.current?.focus();
  }, [location.pathname, location.search]);

  const mainNavigation = [
    { to: "/", label: "Visão Geral", icon: "home" as const, end: true },
    { to: "/mapa", label: "Mapa", icon: "map" as const },
    { to: "/prioridades", label: "Prioridades", icon: "priorities" as const },
    { to: "/insights", label: "Insights", icon: "insights" as const },
    { to: "/cenarios", label: "Cenarios", icon: "scenarios" as const },
    { to: "/eleitorado", label: "Eleitorado", icon: "electorate" as const },
  ];

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Pular para o conteudo principal
      </a>
      <div className="shape shape-left" />
      <div className="shape shape-right" />
      <div className="app-frame">
        <aside className="app-sidebar slide-up" aria-label="Painel lateral de navegacao">
          <nav className="app-nav app-nav-primary" aria-label="Navegação principal">
            {mainNavigation.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <NavIcon name={item.icon} className="nav-icon" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <nav className="app-nav app-nav-admin" aria-label="Navegação técnica">
            <span className="nav-section-label">Complementar</span>
            <NavLink to="/territorio/perfil">
              <NavIcon name="territory" className="nav-icon" />
              Território 360
            </NavLink>
            <NavLink to="/briefs">
              <NavIcon name="briefs" className="nav-icon" />
              Briefs
            </NavLink>
            <NavLink to="/admin">
              <NavIcon name="admin" className="nav-icon" />
              Admin
            </NavLink>
          </nav>
        </aside>

        <div className="app-main">
          <header className="app-header fade-in">
            <div className="app-header-left">
              <p className="eyebrow">Inteligência Territorial</p>
              <h1>Painel de Inteligência Territorial</h1>
            </div>
            <div className="app-header-right">
              <p className="header-note">Diamantina/MG</p>
              <span className="header-badge">API v1</span>
            </div>
          </header>

          <main
            id="main-content"
            ref={mainContentRef}
            className="app-content slide-up delay-1"
            tabIndex={-1}
          >
            {children ?? <Outlet />}
          </main>
        </div>
      </div>
    </div>
  );
}

