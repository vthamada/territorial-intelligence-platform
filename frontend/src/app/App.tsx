import { useEffect, useRef, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { emitTelemetry } from "../shared/observability/telemetry";

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
    { to: "/", label: "Visao Geral", end: true },
    { to: "/prioridades", label: "Prioridades" },
    { to: "/mapa", label: "Mapa" },
    { to: "/insights", label: "Insights" },
    { to: "/cenarios", label: "Cenarios" },
    { to: "/briefs", label: "Briefs" },
    { to: "/territorio/perfil", label: "Territorio 360" },
    { to: "/eleitorado", label: "Eleitorado" }
  ];

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Pular para o conteudo principal
      </a>
      <div className="shape shape-left" />
      <div className="shape shape-right" />
      <header className="app-header fade-in">
        <div>
          <p className="eyebrow">Inteligencia Territorial</p>
          <h1>QG Estrategico</h1>
        </div>
        <p className="header-note">Diamantina/MG - API v1</p>
      </header>

      <nav className="app-nav app-nav-primary slide-up" aria-label="Navegacao principal">
        {mainNavigation.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <nav className="app-nav app-nav-admin slide-up delay-1" aria-label="Navegacao tecnica">
        <span className="nav-section-label">Camada tecnica</span>
        <NavLink to="/admin">Admin</NavLink>
      </nav>

      <main
        id="main-content"
        ref={mainContentRef}
        className="app-content slide-up delay-1"
        tabIndex={-1}
      >
        {children ?? <Outlet />}
      </main>
    </div>
  );
}

