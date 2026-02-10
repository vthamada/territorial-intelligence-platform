import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StateBlock } from "./StateBlock";

describe("StateBlock", () => {
  it("shows request id and calls retry handler", async () => {
    const onRetry = vi.fn();
    render(
      <StateBlock
        tone="error"
        title="Falha"
        message="Erro ao consultar API"
        requestId="req-01"
        onRetry={onRetry}
      />
    );

    expect(screen.getByText("Falha")).toBeInTheDocument();
    expect(screen.getByText("Erro ao consultar API")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-01")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders empty state without retry button", () => {
    render(<StateBlock tone="empty" title="Vazio" message="Nenhum dado." />);
    expect(screen.getByText("Vazio")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });
});
