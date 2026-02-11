import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StrategicIndexCard } from "./StrategicIndexCard";

describe("StrategicIndexCard", () => {
  it("renders label, value, status and trend text", () => {
    render(
      <StrategicIndexCard
        label="Criticos"
        value="4"
        status="critical"
        trend="up"
        helper="itens de maior prioridade"
      />
    );

    expect(screen.getByText("Criticos")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("critico")).toBeInTheDocument();
    expect(screen.getByText("tendencia: subindo")).toBeInTheDocument();
    expect(screen.getByText("itens de maior prioridade")).toBeInTheDocument();
  });
});
