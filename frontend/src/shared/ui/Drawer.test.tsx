import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Drawer } from "./Drawer";

describe("Drawer", () => {
  it("renders title and children when open", () => {
    render(
      <Drawer open={true} onClose={vi.fn()} title="Detalhes">
        <p>Conteudo do drawer</p>
      </Drawer>
    );
    expect(screen.getByRole("dialog", { name: "Detalhes" })).toBeInTheDocument();
    expect(screen.getByText("Conteudo do drawer")).toBeInTheDocument();
    expect(screen.getByText("Detalhes")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    render(
      <Drawer open={true} onClose={onClose} title="Painel">
        <p>Corpo</p>
      </Drawer>
    );
    await userEvent.click(screen.getByRole("button", { name: "Fechar painel" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose on Escape key", async () => {
    const onClose = vi.fn();
    render(
      <Drawer open={true} onClose={onClose} title="Painel">
        <p>Corpo</p>
      </Drawer>
    );
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("is hidden when closed", () => {
    render(
      <Drawer open={false} onClose={vi.fn()} title="Oculto">
        <p>Invisivel</p>
      </Drawer>
    );
    expect(screen.getByRole("dialog", { hidden: true })).toHaveAttribute("aria-hidden", "true");
  });
});
