import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChoroplethMiniMap } from "./ChoroplethMiniMap";

describe("ChoroplethMiniMap", () => {
  it("renders fallback when geometries are missing", () => {
    render(
      <ChoroplethMiniMap
        items={[
          {
            territoryId: "t-1",
            territoryName: "Territorio 1",
            value: 10,
            geometry: null
          }
        ]}
      />
    );

    expect(screen.getByText("Sem geometria valida para renderizar mapa.")).toBeInTheDocument();
  });

  it("calls onSelect when a region path is clicked", async () => {
    const onSelect = vi.fn();
    render(
      <ChoroplethMiniMap
        items={[
          {
            territoryId: "t-1",
            territoryName: "Territorio 1",
            value: 10,
            geometry: {
              type: "Polygon",
              coordinates: [
                [
                  [-43.0, -18.0],
                  [-43.0, -17.5],
                  [-42.5, -17.5],
                  [-42.5, -18.0],
                  [-43.0, -18.0]
                ]
              ]
            }
          }
        ]}
        onSelect={onSelect}
      />
    );

    const path = document.querySelector(".choropleth-path");
    expect(path).not.toBeNull();
    if (!path) {
      return;
    }
    await userEvent.click(path);
    expect(onSelect).toHaveBeenCalledWith("t-1");
  });
});
