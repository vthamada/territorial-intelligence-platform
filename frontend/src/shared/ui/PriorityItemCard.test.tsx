import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PriorityItemCard } from "./PriorityItemCard";

describe("PriorityItemCard", () => {
  it("renders priority context and profile link", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <PriorityItemCard
          item={{
            territory_id: "3121605",
            territory_name: "Diamantina",
            territory_level: "municipio",
            domain: "saude",
            indicator_code: "DATASUS_APS_COBERTURA",
            indicator_name: "Cobertura APS",
            value: 70,
            unit: "%",
            score: 91.3,
            trend: "stable",
            status: "critical",
            rationale: ["Racional de teste"],
            evidence: {
              indicator_code: "DATASUS_APS_COBERTURA",
              reference_period: "2025",
              source: "DATASUS",
              dataset: "datasus_health"
            }
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "Diamantina" })).toBeInTheDocument();
    expect(screen.getByText("Racional de teste")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir perfil" })).toHaveAttribute("href", "/territorio/3121605");
    expect(screen.getByRole("link", { name: "Ver no mapa" })).toHaveAttribute(
      "href",
      "/mapa?metric=DATASUS_APS_COBERTURA&period=2025&territory_id=3121605"
    );
  });
});
