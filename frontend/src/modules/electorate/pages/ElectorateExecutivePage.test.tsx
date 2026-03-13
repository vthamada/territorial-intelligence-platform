import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getElectorateCandidateTerritories,
  getElectorateElectionContext,
  getElectorateHistory,
  getElectoratePollingPlaces,
  getElectorateSummary,
} from "../../../shared/api/qg";
import { ElectorateExecutivePage } from "./ElectorateExecutivePage";

vi.mock("../../../shared/api/qg", () => ({
  getElectorateSummary: vi.fn(),
  getElectorateHistory: vi.fn(),
  getElectoratePollingPlaces: vi.fn(),
  getElectorateElectionContext: vi.fn(),
  getElectorateCandidateTerritories: vi.fn(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

function seedDefaultMocks() {
  vi.mocked(getElectorateSummary).mockResolvedValue({
    level: "município",
    year: 2024,
    metadata: {
      source_name: "silver.fact_electorate",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: "voters",
      notes: null,
    },
    total_voters: 12000,
    turnout: 8000,
    turnout_rate: 80,
    abstention_rate: 20,
    blank_rate: 2,
    null_rate: 3,
    by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
    by_age: [
      { label: "25 a 29 anos", voters: 3940, share_percent: 32.83 },
      { label: "20 anos", voters: 527, share_percent: 4.39 },
      { label: "19 anos", voters: 494, share_percent: 4.12 },
      { label: "18 anos", voters: 414, share_percent: 3.45 },
      { label: "17 anos", voters: 166, share_percent: 1.38 },
      { label: "16 anos", voters: 72, share_percent: 0.6 },
    ],
    by_education: [],
  });

  vi.mocked(getElectorateHistory).mockResolvedValue({
    level: "município",
    metadata: {
      source_name: "silver.fact_electorate + silver.fact_election_result",
      updated_at: null,
      coverage_note: "historical_series",
      unit: "voters",
      notes: null,
    },
    items: [
      {
        year: 2024,
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
      },
      {
        year: 2022,
        total_voters: 11500,
        turnout: 7600,
        turnout_rate: 77,
        abstention_rate: 23,
        blank_rate: 1.7,
        null_rate: 2.4,
      },
    ],
  });

  vi.mocked(getElectoratePollingPlaces).mockResolvedValue({
    metric: "voters",
    year: 2024,
    metadata: {
      source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)",
      updated_at: null,
      coverage_note: "polling_place_ranked",
      unit: "voters",
      notes: null,
    },
    items: [
      {
        territory_id: "pp-1",
        territory_name: "UEMG (ANTIGA FEVALE)",
        territory_level: "polling_place",
        metric: "voters",
        value: 2327,
        year: 2024,
        polling_place_name: "UEMG (ANTIGA FEVALE)",
        polling_place_code: "101",
        district_name: "Centro",
        zone_codes: ["101"],
        section_count: 13,
        sections: ["41", "177", "212"],
        voters_total: 2327,
        share_percent: 6,
      },
      {
        territory_id: "pp-2",
        territory_name: "E. E. PROF. ISABEL MOTA",
        territory_level: "polling_place",
        metric: "voters",
        value: 2453,
        year: 2024,
        polling_place_name: "E. E. PROF. ISABEL MOTA",
        polling_place_code: "102",
        district_name: "Rio Grande",
        zone_codes: ["101"],
        section_count: 8,
        sections: ["58", "59", "60", "212", "234", "276"],
        voters_total: 2453,
        share_percent: 6.35,
      },
    ],
  });

  vi.mocked(getElectorateElectionContext).mockResolvedValue({
    level: "municipality",
    year: 2024,
    election_round: 1,
    office: "PREFEITO",
    election_type: "municipal",
    metadata: {
      source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
      updated_at: null,
      coverage_note: "candidate_context",
      unit: "votes",
      notes: null,
    },
    total_votes: 10000,
    available_offices: [
      { office: "PREFEITO", election_round: 1, election_type: "municipal", total_votes: 10000, is_primary: true },
      { office: "VEREADOR", election_round: 1, election_type: "municipal", total_votes: 9800, is_primary: false },
    ],
    items: [
      {
        candidate_id: "cand-1",
        candidate_number: "15",
        candidate_name: "João Silva",
        ballot_name: "João",
        party_abbr: "MDB",
        party_number: "15",
        party_name: "Movimento Democrático Brasileiro",
        votes: 5200,
        share_percent: 52,
      },
      {
        candidate_id: "cand-2",
        candidate_number: "40",
        candidate_name: "Maria Souza",
        ballot_name: "Maria",
        party_abbr: "PSB",
        party_number: "40",
        party_name: "Partido Socialista Brasileiro",
        votes: 4800,
        share_percent: 48,
      },
    ],
  });

  vi.mocked(getElectorateCandidateTerritories).mockImplementation(async (params) => {
    if (params.candidate_id === "cand-2") {
      return {
        level: "electoral_section",
        aggregate_by: "polling_place",
        year: 2024,
        election_round: 1,
        office: "PREFEITO",
        election_type: "municipal",
        candidate_id: "cand-2",
        metadata: {
          source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
          updated_at: null,
          coverage_note: "candidate_territorial",
          unit: "votes",
          notes: null,
        },
        items: [
          {
            territory_id: "pp-2",
            territory_name: "Escola A",
            territory_level: "polling_place",
            candidate_id: "cand-2",
            candidate_number: "40",
            candidate_name: "Maria Souza",
            ballot_name: "Maria",
            party_abbr: "PSB",
            party_number: "40",
            party_name: "Partido Socialista Brasileiro",
            votes: 1300,
            share_percent: 27.1,
            polling_place_name: "Escola A",
            polling_place_code: "202",
            district_name: "Rio Grande",
            zone_codes: ["101"],
            section_count: 4,
            sections: ["10", "11", "12", "13"],
            polling_place_section_count: 5,
            polling_place_sections: ["10", "11", "12", "13", "14"],
          },
        ],
      };
    }

    return {
      level: "electoral_section",
      aggregate_by: "polling_place",
      year: 2024,
      election_round: 1,
      office: "PREFEITO",
      election_type: "municipal",
      candidate_id: "cand-1",
      metadata: {
        source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
        updated_at: null,
        coverage_note: "candidate_territorial",
        unit: "votes",
        notes: null,
      },
      items: [
        {
          territory_id: "pp-1",
          territory_name: "UEMG (ANTIGA FEVALE)",
          territory_level: "polling_place",
          candidate_id: "cand-1",
          candidate_number: "15",
          candidate_name: "João Silva",
          ballot_name: "João",
          party_abbr: "MDB",
          party_number: "15",
          party_name: "Movimento Democrático Brasileiro",
          votes: 1450,
          share_percent: 27.9,
          polling_place_name: "UEMG (ANTIGA FEVALE)",
          polling_place_code: "101",
          district_name: "Centro",
          zone_codes: ["101"],
          section_count: 13,
          sections: ["41", "177", "212"],
          polling_place_section_count: 13,
          polling_place_sections: ["41", "177", "212"],
        },
      ],
    };
  });
}

describe("ElectorateExecutivePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedDefaultMocks();
  });

  it("applies electorate filters only on submit", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateHistory).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectoratePollingPlaces).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateElectionContext).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateCandidateTerritories).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.selectOptions(screen.getByLabelText("Métrica do ranking"), "abstention_rate");
    expect(getElectoratePollingPlaces).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() =>
      expect(vi.mocked(getElectorateSummary).mock.calls).toContainEqual([
        expect.objectContaining({ level: "municipality", year: 2022 }),
      ]),
    );
    await waitFor(() =>
      expect(vi.mocked(getElectoratePollingPlaces).mock.calls).toContainEqual([
        expect.objectContaining({ year: 2022, metric: "abstention_rate", limit: 200 }),
      ]),
    );
    await waitFor(() =>
      expect(vi.mocked(getElectorateElectionContext).mock.calls).toContainEqual([
        expect.objectContaining({ level: "municipality", year: 2024, limit: 8 }),
      ]),
    );
  });

  it("falls back to latest available year when selected year has no electorate data", async () => {
    vi.mocked(getElectorateSummary)
      .mockResolvedValueOnce({
        level: "município",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: [],
      })
      .mockResolvedValueOnce({
        level: "município",
        year: null,
        metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
        total_voters: 0,
        turnout: 0,
        turnout_rate: null,
        abstention_rate: null,
        blank_rate: null,
        null_rate: null,
        by_sex: [],
        by_age: [],
        by_education: [],
      })
      .mockResolvedValueOnce({
        level: "município",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: [],
      });

    vi.mocked(getElectorateHistory)
      .mockResolvedValueOnce({
        level: "município",
        metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
        items: [{ year: 2024, total_voters: 12000, turnout: 8000, turnout_rate: 80, abstention_rate: 20, blank_rate: 2, null_rate: 3 }],
      })
      .mockResolvedValueOnce({
        level: "município",
        metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
        items: [],
      })
      .mockResolvedValueOnce({
        level: "município",
        metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
        items: [{ year: 2024, total_voters: 12000, turnout: 8000, turnout_rate: 80, abstention_rate: 20, blank_rate: 2, null_rate: 3 }],
      });

    vi.mocked(getElectoratePollingPlaces)
      .mockResolvedValueOnce({
        metric: "voters",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
        items: [{ territory_id: "pp-1", territory_name: "UEMG (ANTIGA FEVALE)", territory_level: "polling_place", metric: "voters", value: 2327, year: 2024, polling_place_name: "UEMG (ANTIGA FEVALE)", polling_place_code: "101", district_name: "Centro", zone_codes: ["101"], section_count: 13, sections: ["41", "177", "212"], voters_total: 2327, share_percent: 6 }],
      })
      .mockResolvedValueOnce({
        metric: "voters",
        year: null,
        metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
        items: [],
      })
      .mockResolvedValueOnce({
        metric: "voters",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
        items: [{ territory_id: "pp-1", territory_name: "UEMG (ANTIGA FEVALE)", territory_level: "polling_place", metric: "voters", value: 2327, year: 2024, polling_place_name: "UEMG (ANTIGA FEVALE)", polling_place_code: "101", district_name: "Centro", zone_codes: ["101"], section_count: 13, sections: ["41", "177", "212"], voters_total: 2327, share_percent: 6 }],
      });

    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: "Aplicar filtros" });
    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await screen.findByText("Ano 2022 sem dados consolidados");
    expect(screen.getByText(/Mostrando automaticamente o último recorte com dados \(2024\)/)).toBeInTheDocument();
    expect((await screen.findAllByText("UEMG (ANTIGA FEVALE)")).length).toBeGreaterThan(0);
    expect(screen.getByText("Contexto da eleição")).toBeInTheDocument();
  });

  it("renders election context and allows switching candidate territorial distribution", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);

    expect(await screen.findByText("Cargo em exibição")).toBeInTheDocument();
    expect(screen.getByText("Prefeito")).toBeInTheDocument();
    expect(screen.getByText("João")).toBeInTheDocument();
    expect(screen.getByText("52,00%")).toBeInTheDocument();
    expect(await screen.findByText("UEMG (ANTIGA FEVALE)")).toBeInTheDocument();
    expect(screen.getByText("1.450")).toBeInTheDocument();
    expect(screen.getByText("13 seções com votos")).toBeInTheDocument();
    expect(screen.getAllByText("Seções: 41, 177, 212").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "Ver distribuição" }));

    await waitFor(() =>
      expect(vi.mocked(getElectorateCandidateTerritories).mock.calls).toContainEqual([
        expect.objectContaining({ candidate_id: "cand-2", aggregate_by: "polling_place", year: 2024 }),
      ]),
    );
    expect(await screen.findByText("Escola A")).toBeInTheDocument();
    expect(screen.getByText("1.300")).toBeInTheDocument();
    expect(screen.getByText("4 de 5 seções com votos")).toBeInTheDocument();
    expect(screen.getByText("Seções: 10, 11, 12, 13")).toBeInTheDocument();
  });

  it("allows switching the office shown in the election context", async () => {
    vi.mocked(getElectorateElectionContext)
      .mockResolvedValueOnce({
        level: "municipality",
        year: 2024,
        election_round: 1,
        office: "PREFEITO",
        election_type: "municipal",
        metadata: {
          source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
          updated_at: null,
          coverage_note: "candidate_context",
          unit: "votes",
          notes: null,
        },
        total_votes: 10000,
        available_offices: [
          { office: "PREFEITO", election_round: 1, election_type: "municipal", total_votes: 10000, is_primary: true },
          { office: "VEREADOR", election_round: 1, election_type: "municipal", total_votes: 9800, is_primary: false },
        ],
        items: [
          {
            candidate_id: "cand-1",
            candidate_number: "15",
            candidate_name: "João Silva",
            ballot_name: "João",
            party_abbr: "MDB",
            party_number: "15",
            party_name: "Movimento Democrático Brasileiro",
            votes: 5200,
            share_percent: 52,
          },
        ],
      })
      .mockResolvedValueOnce({
        level: "municipality",
        year: 2024,
        election_round: 1,
        office: "VEREADOR",
        election_type: "municipal",
        metadata: {
          source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
          updated_at: null,
          coverage_note: "candidate_context",
          unit: "votes",
          notes: null,
        },
        total_votes: 9800,
        available_offices: [
          { office: "PREFEITO", election_round: 1, election_type: "municipal", total_votes: 10000, is_primary: false },
          { office: "VEREADOR", election_round: 1, election_type: "municipal", total_votes: 9800, is_primary: true },
        ],
        items: [
          {
            candidate_id: "cand-9",
            candidate_number: "12345",
            candidate_name: "Carlos Pereira",
            ballot_name: "Carlos",
            party_abbr: "PSD",
            party_number: "55",
            party_name: "Partido Social Democrático",
            votes: 1400,
            share_percent: 14.29,
          },
        ],
      });

    vi.mocked(getElectorateCandidateTerritories)
      .mockResolvedValueOnce({
        level: "electoral_section",
        aggregate_by: "polling_place",
        year: 2024,
        election_round: 1,
        office: "PREFEITO",
        election_type: "municipal",
        candidate_id: "cand-1",
        metadata: {
          source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
          updated_at: null,
          coverage_note: "candidate_territorial",
          unit: "votes",
          notes: null,
        },
        items: [],
      })
      .mockResolvedValueOnce({
        level: "electoral_section",
        aggregate_by: "polling_place",
        year: 2024,
        election_round: 1,
        office: "VEREADOR",
        election_type: "municipal",
        candidate_id: "cand-9",
        metadata: {
          source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
          updated_at: null,
          coverage_note: "candidate_territorial",
          unit: "votes",
          notes: null,
        },
        items: [],
      });

    renderWithQueryClient(<ElectorateExecutivePage />);

    expect(await screen.findByLabelText("Cargo da eleição")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Cargo da eleição"), "VEREADOR::1");

    await waitFor(() =>
      expect(vi.mocked(getElectorateElectionContext).mock.calls).toContainEqual([
        expect.objectContaining({
          level: "municipality",
          year: 2024,
          office: "VEREADOR",
          election_round: 1,
          limit: 8,
        }),
      ]),
    );
    await waitFor(() =>
      expect(vi.mocked(getElectorateCandidateTerritories).mock.calls).toContainEqual([
        expect.objectContaining({
          candidate_id: "cand-9",
          aggregate_by: "polling_place",
          year: 2024,
          office: "VEREADOR",
          election_round: 1,
        }),
      ]),
    );
    expect(await screen.findByText("Vereador")).toBeInTheDocument();
    expect(screen.getByText("Carlos")).toBeInTheDocument();
  });

  it("explains when nominal candidate distribution is only available by electoral zone", async () => {
    vi.mocked(getElectorateElectionContext).mockResolvedValueOnce({
      level: "municipality",
      year: 2024,
      election_round: 1,
      office: "PREFEITO",
      election_type: "municipal",
      metadata: {
        source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
        updated_at: null,
        coverage_note: "candidate_context",
        unit: "votes",
        notes: "electorate_election_context_v1|source_level=electoral_zone",
      },
      total_votes: 10000,
      available_offices: [
        { office: "PREFEITO", election_round: 1, election_type: "municipal", total_votes: 10000, is_primary: true },
      ],
      items: [
        {
          candidate_id: "cand-1",
          candidate_number: "15",
          candidate_name: "Jo?o Silva",
          ballot_name: "Jo?o",
          party_abbr: "MDB",
          party_number: "15",
          party_name: "Movimento Democrático Brasileiro",
          votes: 5200,
          share_percent: 52,
        },
      ],
    });
    vi.mocked(getElectorateCandidateTerritories).mockResolvedValueOnce({
      level: "electoral_section",
      aggregate_by: "polling_place",
      year: 2024,
      election_round: 1,
      office: "PREFEITO",
      election_type: "municipal",
      candidate_id: "cand-1",
      metadata: {
        source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
        updated_at: null,
        coverage_note: "candidate_territorial",
        unit: "votes",
        notes: "candidate_territories_unavailable|source_level=electoral_zone|requested_aggregate=polling_place",
      },
      items: [],
    });

    renderWithQueryClient(<ElectorateExecutivePage />);

    expect(await screen.findByText("Contexto nominal agregado a partir de zona eleitoral")).toBeInTheDocument();
    expect(await screen.findByText((content) => content.includes("Distribuição nominal disponível apenas em zona eleitoral"))).toBeInTheDocument();
    expect(document.body.textContent).toContain("A fonte nominal carregada nesta rodada");
    expect(document.body.textContent).toContain("agregado municipal");
  });

  it("groups polling places by district and hides duplicate metric column for voter ranking", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);

    expect(await screen.findByRole("heading", { name: "Centro" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rio Grande" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Indicador selecionado" })).not.toBeInTheDocument();
    expect(screen.getByText("13 seções")).toBeInTheDocument();
    expect(screen.getByText("Seções: 41, 177, 212")).toBeInTheDocument();
  });

  it("aggregates ages 16 to 20 into a single electorate composition bucket", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);

    await userEvent.click(await screen.findByRole("button", { name: "Idade" }));

    expect(screen.getByText("16 a 20 anos")).toBeInTheDocument();
    expect(screen.getByText("1.673")).toBeInTheDocument();
    expect(screen.queryByText("16 anos")).not.toBeInTheDocument();
    expect(screen.queryByText("17 anos")).not.toBeInTheDocument();
    expect(screen.queryByText("18 anos")).not.toBeInTheDocument();
    expect(screen.queryByText("19 anos")).not.toBeInTheDocument();
    expect(screen.queryByText("20 anos")).not.toBeInTheDocument();
  });

  it("uses historical metrics in resumo executivo when summary lacks rates for the selected year", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);
    await screen.findByLabelText("Ano");

    vi.mocked(getElectorateSummary).mockImplementation(async (params) => {
      if (params?.year === 2022) {
        return {
          level: "município",
          year: 2022,
          metadata: {
            source_name: "silver.fact_electorate",
            updated_at: null,
            coverage_note: "territorial_aggregated",
            unit: "voters",
            notes: null,
          },
          total_voters: 38097,
          turnout: null,
          turnout_rate: null,
          abstention_rate: null,
          blank_rate: null,
          null_rate: null,
          by_sex: [{ label: "FEMININO", voters: 20152, share_percent: 52.9 }],
          by_age: [],
          by_education: [],
        };
      }
      throw new Error("Unexpected summary request");
    });
    vi.mocked(getElectorateHistory).mockImplementation(async (params) => {
      if (params?.year === 2022) {
        return {
          level: "município",
          metadata: {
            source_name: "silver.fact_electorate + silver.fact_election_result",
            updated_at: null,
            coverage_note: "historical_series",
            unit: "voters",
            notes: null,
          },
          items: [
            {
              year: 2024,
              total_voters: 38607,
              turnout: 27941,
              turnout_rate: 72.372886,
              abstention_rate: 27.627114,
              blank_rate: 5.540246,
              null_rate: 7.616048,
            },
            {
              year: 2022,
              total_voters: 38097,
              turnout: 28448,
              turnout_rate: 75.106265,
              abstention_rate: 24.893735,
              blank_rate: 6.538245,
              null_rate: 3.7964,
            },
          ],
        };
      }
      throw new Error("Unexpected history request");
    });
    vi.mocked(getElectoratePollingPlaces).mockImplementation(async (params) => {
      if (params?.year === 2022) {
        return {
          metric: "voters",
          year: 2022,
          metadata: {
            source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)",
            updated_at: null,
            coverage_note: "polling_place_ranked",
            unit: "voters",
            notes: null,
          },
          items: [],
        };
      }
      throw new Error("Unexpected polling-place request");
    });
    vi.mocked(getElectorateElectionContext).mockImplementation(async (params) => {
      if (params?.year === 2022) {
        return {
          level: "municipality",
          year: 2022,
          election_round: 1,
          office: "PRESIDENTE",
          election_type: "geral",
          metadata: {
            source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
            updated_at: null,
            coverage_note: "candidate_context",
            unit: "votes",
            notes: null,
          },
          total_votes: 27761,
          available_offices: [
            { office: "PRESIDENTE", election_round: 1, election_type: "geral", total_votes: 27761, is_primary: true },
          ],
          items: [
            {
              candidate_id: "cand-pt",
              candidate_number: "13",
              candidate_name: "Lula",
              ballot_name: "Lula",
              party_abbr: "PT",
              party_number: "13",
              party_name: "Partido dos Trabalhadores",
              votes: 14000,
              share_percent: 50.43,
            },
          ],
        };
      }
      throw new Error("Unexpected election-context request");
    });
    vi.mocked(getElectorateCandidateTerritories).mockImplementation(async (params) => {
      if (params.candidate_id === "cand-pt") {
        return {
          level: "electoral_section",
          aggregate_by: "polling_place",
          year: 2022,
          election_round: 1,
          office: "PRESIDENTE",
          election_type: "geral",
          candidate_id: "cand-pt",
          metadata: {
            source_name: "silver.dim_election + silver.dim_candidate + silver.fact_candidate_vote",
            updated_at: null,
            coverage_note: "candidate_territorial",
            unit: "votes",
            notes: null,
          },
          items: [],
        };
      }
      throw new Error("Unexpected candidate-territories request");
    });

    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    const executiveSummaryPanel = screen.getByRole("heading", { name: "Resumo executivo" }).closest(".panel");
    expect(executiveSummaryPanel).not.toBeNull();
    const summaryScope = within(executiveSummaryPanel as HTMLElement);

    expect(await summaryScope.findByText("28.448")).toBeInTheDocument();
    expect(summaryScope.getByText("75,11%")).toBeInTheDocument();
    expect(summaryScope.getByText("24,89%")).toBeInTheDocument();
    expect(summaryScope.getByText("6,54%")).toBeInTheDocument();
    expect(summaryScope.getByText("3,80%")).toBeInTheDocument();
  });

  it("shows fallback error when selected year has no data and fallback fails", async () => {
    let summaryUndefinedCalls = 0;
    let historyUndefinedCalls = 0;
    let pollingUndefinedCalls = 0;

    vi.mocked(getElectorateSummary).mockImplementation(async (params) => {
      const year = params?.year;
      if (year === 2022) {
        return {
          level: "munic?pio",
          year: null,
          metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
          total_voters: 0,
          turnout: 0,
          turnout_rate: null,
          abstention_rate: null,
          blank_rate: null,
          null_rate: null,
          by_sex: [],
          by_age: [],
          by_education: [],
        };
      }
      summaryUndefinedCalls += 1;
      if (summaryUndefinedCalls >= 2) {
        throw new Error("Fallback summary unavailable");
      }
      return {
        level: "munic?pio",
        year: 2024,
        metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: [],
      };
    });
    vi.mocked(getElectorateHistory).mockImplementation(async (params) => {
      if (params?.year === 2022) {
        return {
          level: "munic?pio",
          metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
          items: [],
        };
      }
      historyUndefinedCalls += 1;
      if (historyUndefinedCalls >= 2) {
        throw new Error("Fallback history unavailable");
      }
      return {
        level: "munic?pio",
        metadata: { source_name: "silver.fact_electorate + silver.fact_election_result", updated_at: null, coverage_note: "historical_series", unit: "voters", notes: null },
        items: [{ year: 2024, total_voters: 12000, turnout: 8000, turnout_rate: 80, abstention_rate: 20, blank_rate: 2, null_rate: 3 }],
      };
    });
    vi.mocked(getElectoratePollingPlaces).mockImplementation(async (params) => {
      const metric = (params?.metric ?? "voters") as "voters";
      if (params?.year === 2022) {
        return {
          metric,
          year: null,
          metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
          items: [],
        };
      }
      pollingUndefinedCalls += 1;
      if (pollingUndefinedCalls >= 2) {
        throw new Error("Fallback polling places unavailable");
      }
      return {
        metric,
        year: 2024,
        metadata: { source_name: "silver.fact_electorate + silver.dim_territory(metadata.polling_place_*)", updated_at: null, coverage_note: "polling_place_ranked", unit: "voters", notes: null },
        items: [{ territory_id: "pp-1", territory_name: "UEMG (ANTIGA FEVALE)", territory_level: "polling_place", metric, value: 2327, year: 2024, polling_place_name: "UEMG (ANTIGA FEVALE)", polling_place_code: "101", district_name: "Centro", zone_codes: ["101"], section_count: 13, sections: ["41", "177", "212"], voters_total: 2327, share_percent: 6 }],
      };
    });

    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: "Aplicar filtros" });
    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    expect(await screen.findByText("Falha ao carregar fallback do eleitorado")).toBeInTheDocument();
  });
});
