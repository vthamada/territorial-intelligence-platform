import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App shell", () => {
  it("renders navigation and child content", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App>
          <div>Conteudo de teste</div>
        </App>
      </MemoryRouter>
    );

    expect(screen.getByText("QG Estrategico")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Visao Geral" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Prioridades" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Mapa" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Insights" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cenarios" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Briefs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Territorio 360" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Eleitorado" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Pular para o conteudo principal" })).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main-content");
    expect(main).toHaveFocus();
    expect(screen.getByText("Conteudo de teste")).toBeInTheDocument();
  });
});
