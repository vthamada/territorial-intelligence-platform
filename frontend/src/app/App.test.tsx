import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App shell", () => {
  it("renders navigation and child content", () => {
    render(
      <MemoryRouter>
        <App>
          <div>Conteudo de teste</div>
        </App>
      </MemoryRouter>
    );

    expect(screen.getByText("Painel Operacional")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Saude Ops" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Execucoes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Checks" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Conectores" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Territorios e Indicadores" })).toBeInTheDocument();
    expect(screen.getByText("Conteudo de teste")).toBeInTheDocument();
  });
});
