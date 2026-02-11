import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

type AppProps = {
  children?: ReactNode;
};

export function App({ children }: AppProps) {
  return (
    <div className="app-shell">
      <div className="shape shape-left" />
      <div className="shape shape-right" />
      <header className="app-header fade-in">
        <div>
          <p className="eyebrow">Inteligencia Territorial</p>
          <h1>Painel Operacional</h1>
        </div>
        <p className="header-note">Diamantina/MG - API v1</p>
      </header>

      <nav className="app-nav slide-up">
        <NavLink to="/" end>
          Saude Ops
        </NavLink>
        <NavLink to="/ops/runs">Execucoes</NavLink>
        <NavLink to="/ops/checks">Checks</NavLink>
        <NavLink to="/ops/connectors">Conectores</NavLink>
        <NavLink to="/territory/indicators">Territorios e Indicadores</NavLink>
      </nav>

      <main className="app-content slide-up delay-1">{children ?? <Outlet />}</main>
    </div>
  );
}

