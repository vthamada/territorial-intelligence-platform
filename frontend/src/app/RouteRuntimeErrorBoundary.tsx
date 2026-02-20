import { Component, type ErrorInfo, type ReactNode } from "react";
import { emitTelemetry } from "../shared/observability/telemetry";
import { StateBlock } from "../shared/ui/StateBlock";

type RouteRuntimeErrorBoundaryProps = {
  children: ReactNode;
  routeLabel?: string;
};

type RouteRuntimeErrorBoundaryState = {
  hasError: boolean;
  message: string;
};

function resolveRuntimeErrorMessage(error: unknown) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Ocorreu um erro inesperado durante a renderizacao desta tela.";
}

export class RouteRuntimeErrorBoundary extends Component<
  RouteRuntimeErrorBoundaryProps,
  RouteRuntimeErrorBoundaryState
> {
  state: RouteRuntimeErrorBoundaryState = {
    hasError: false,
    message: "",
  };

  static getDerivedStateFromError(error: unknown): RouteRuntimeErrorBoundaryState {
    return {
      hasError: true,
      message: resolveRuntimeErrorMessage(error),
    };
  }

  componentDidCatch(error: unknown, errorInfo: ErrorInfo) {
    emitTelemetry({
      category: "frontend_error",
      name: "route_runtime_error",
      severity: "error",
      attributes: {
        route_label: this.props.routeLabel ?? null,
        message: resolveRuntimeErrorMessage(error),
        component_stack: errorInfo.componentStack ?? null,
      },
    });
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      message: "",
    });
  };

  render() {
    if (this.state.hasError) {
      const title = this.props.routeLabel ? `Falha na tela: ${this.props.routeLabel}` : "Falha na tela";
      return (
        <StateBlock
          tone="error"
          title={title}
          message={this.state.message}
          onRetry={this.handleRetry}
        />
      );
    }
    return this.props.children;
  }
}

