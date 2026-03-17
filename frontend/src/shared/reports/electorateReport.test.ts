import { describe, expect, it } from "vitest";
import { buildElectorateReportHtml } from "./electorateReport";

describe("buildElectorateReportHtml", () => {
  it("keeps table section titles inside thead and hides duplicate indicator for voters", () => {
    const html = buildElectorateReportHtml({
      generatedAt: new Date("2026-03-16T16:46:18Z"),
      year: 2024,
      metricLabel: "Total de eleitores",
      officeLabel: "Prefeito",
      electionTypeLabel: "Municipal",
      electionRoundLabel: "1º turno",
      candidateLabel: "João",
      sections: ["summary", "history", "election_context", "candidate_territories", "polling_places", "composition"],
      summary: {
        level: "municipality",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "Feminino", voters: 6200, share_percent: 51.67 }],
        by_age: [{ label: "25 a 29 anos", voters: 2100, share_percent: 17.5 }],
        by_education: [{ label: "Superior completo", voters: 900, share_percent: 7.5 }],
      },
      summaryTurnout: 8000,
      summaryTurnoutRate: 80,
      summaryAbstentionRate: 20,
      summaryBlankRate: 2,
      summaryNullRate: 3,
      history: {
        level: "municipality",
        metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
        items: [{ year: 2024, total_voters: 12000, turnout: 8000, turnout_rate: 80, abstention_rate: 20, blank_rate: 2, null_rate: 3 }],
      },
      electionContext: {
        level: "municipality",
        year: 2024,
        election_round: 1,
        office: "Prefeito",
        election_type: "Municipal",
        metadata: { source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote", updated_at: null, coverage_note: "candidate_context", unit: "votes", notes: null },
        total_votes: 10000,
        available_offices: [{ office: "Prefeito", election_round: 1, election_type: "Municipal", total_votes: 10000, is_primary: true }],
        items: [{ candidate_id: "cand-1", candidate_number: "15", candidate_name: "João Silva", ballot_name: "João", party_abbr: "MDB", party_number: "15", party_name: "MDB", votes: 5200, share_percent: 52 }],
      },
      candidateTerritories: {
        level: "electoral_section",
        aggregate_by: "polling_place",
        year: 2024,
        election_round: 1,
        office: "Prefeito",
        election_type: "Municipal",
        candidate_id: "cand-1",
        metadata: { source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote", updated_at: null, coverage_note: "candidate_territorial", unit: "votes", notes: null },
        items: [{ territory_id: "pp-1", territory_name: "Escola A", territory_level: "polling_place", candidate_id: "cand-1", candidate_number: "15", candidate_name: "João Silva", ballot_name: "João", party_abbr: "MDB", party_number: "15", party_name: "MDB", votes: 1200, share_percent: 24, polling_place_name: "Escola A", polling_place_code: "101", district_name: "Diamantina", zone_codes: ["101"], section_count: 4, sections: ["10", "11", "12", "13"], polling_place_section_count: 5, polling_place_sections: ["10", "11", "12", "13", "14"] }],
      },
      pollingPlaces: {
        metric: "voters",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
        items: [{ territory_id: "pp-1", territory_name: "Escola A", territory_level: "polling_place", metric: "voters", value: 2000, year: 2024, polling_place_name: "Escola A", polling_place_code: "101", district_name: "Diamantina", zone_codes: ["101"], section_count: 5, sections: ["10", "11", "12", "13", "14"], voters_total: 2000, share_percent: 16.67 }],
      },
      ageBreakdown: [{ label: "16 a 20 anos", voters: 1200, share_percent: 10 }],
    });

    expect(html).toContain('class="table-section-title-row"');
    expect(html).toContain('class="table-column-header-row"');
    expect(html).toContain("Ranking de locais de votação");
    expect(html).toContain(".table-section-title");
    expect(html).toContain(".report-section-table { gap: 0; }");
    expect(html).toContain("thead { display: table-header-group; }");
    expect(html).toContain(".table-column-header-row { page-break-after: avoid; break-after: avoid-page; }");
    expect(html).not.toContain(">Indicador<");
  });
});
