import { Link } from "react-router-dom";
import { Panel } from "../../../shared/ui/Panel";

type AdminRouteLink = {
  to: string;
  label: string;
  description: string;
};

const adminLinks: AdminRouteLink[] = [
  {
    to: "/ops/health",
    label: "Saude Ops",
    description: "Saude da API, banco e volume operacional."
  },
  {
    to: "/ops/runs",
    label: "Execucoes",
    description: "Historico de runs de pipeline com filtros e paginacao."
  },
  {
    to: "/ops/checks",
    label: "Checks",
    description: "Resultados dos checks de qualidade e operacao."
  },
  {
    to: "/ops/connectors",
    label: "Conectores",
    description: "Registry de conectores e status por onda."
  },
  {
    to: "/ops/frontend-events",
    label: "Eventos Frontend",
    description: "Telemetria de erros, web vitals e chamadas API do cliente."
  },
  {
    to: "/territory/indicators",
    label: "Territorios e Indicadores",
    description: "Consulta tecnica para depuracao de dados territoriais."
  }
];

export function AdminHubPage() {
  return (
    <div className="page-grid">
      <Panel title="Admin tecnico" subtitle="Camada operacional separada do fluxo executivo do QG">
        <p className="panel-subtitle">
          Use esta area para operacao de dados, validacao de execucoes e troubleshooting tecnico.
        </p>
      </Panel>

      <Panel title="Ferramentas operacionais" subtitle="Atalhos para monitoramento e suporte tecnico">
        <div className="admin-link-grid">
          {adminLinks.map((item) => (
            <article key={item.to} className="admin-link-card">
              <h3>{item.label}</h3>
              <p>{item.description}</p>
              <Link className="inline-link" to={item.to}>
                Abrir {item.label}
              </Link>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
