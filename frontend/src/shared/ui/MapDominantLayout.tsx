import { type ReactNode } from "react";

type MapDominantLayoutProps = {
  map: ReactNode;
  sidebar: ReactNode;
  sidebarOpen: boolean;
};

/**
 * Layout B: full-width map with a collapsible sidebar overlay.
 * The map fills the entire content area; the sidebar slides over it.
 */
export function MapDominantLayout({ map, sidebar, sidebarOpen }: MapDominantLayoutProps) {
  return (
    <div className="map-dominant">
      <div className="map-dominant-canvas">
        {map}
      </div>
      <div className={`map-dominant-sidebar ${sidebarOpen ? "map-dominant-sidebar-open" : ""}`}>
        {sidebar}
      </div>
    </div>
  );
}
