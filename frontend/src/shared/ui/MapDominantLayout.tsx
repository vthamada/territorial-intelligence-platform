import { type ReactNode } from "react";

type MapDominantLayoutProps = {
  map: ReactNode;
  sidebar: ReactNode;
  sidebarOpen: boolean;
};

/**
 * Layout B: dominant map with collapsible executive sidebar.
 * On desktop the sidebar is docked; on narrow screens it stacks below the map.
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
