import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SourceFreshnessBadge } from "./SourceFreshnessBadge";

describe("SourceFreshnessBadge", () => {
  it("renders source metadata fields", () => {
    render(
      <SourceFreshnessBadge
        metadata={{
          source_name: "silver.fact_indicator",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: null,
          notes: null
        }}
      />
    );

    expect(screen.getByRole("status", { name: "Metadados de fonte e atualizacao" })).toBeInTheDocument();
    expect(screen.getByText("Fonte: Indicadores consolidados")).toBeInTheDocument();
    expect(screen.getByText("Atualizacao: sem data")).toBeInTheDocument();
    expect(screen.getByText("Cobertura: Agregado territorial")).toBeInTheDocument();
  });
});
