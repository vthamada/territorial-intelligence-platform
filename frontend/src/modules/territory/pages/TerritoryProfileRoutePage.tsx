import { useParams } from "react-router-dom";
import { TerritoryProfilePage } from "./TerritoryProfilePage";

export function TerritoryProfileRoutePage() {
  const params = useParams<{ territoryId: string }>();
  return <TerritoryProfilePage initialTerritoryId={params.territoryId} />;
}
