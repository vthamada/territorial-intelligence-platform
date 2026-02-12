import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";
import { StateBlock } from "../shared/ui/StateBlock";

function resolveRouteErrorMessage(error: unknown) {
  if (isRouteErrorResponse(error)) {
    if (typeof error.data === "string" && error.data.trim()) {
      return error.data;
    }
    if (error.status === 404) {
      return "A pagina solicitada nao foi encontrada.";
    }
    return `Falha ao abrir a pagina (${error.status}).`;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Ocorreu um erro inesperado ao abrir esta pagina.";
}

export function RouteErrorPage() {
  const error = useRouteError();
  const message = resolveRouteErrorMessage(error);

  return (
    <div className="page-grid">
      <StateBlock
        tone="error"
        title="Falha ao carregar pagina"
        message={message}
      />
      <div className="quick-actions">
        <Link className="quick-action-link" to="/">
          Voltar para Visao Geral
        </Link>
        <Link className="quick-action-link" to="/admin">
          Ir para Admin
        </Link>
      </div>
    </div>
  );
}

