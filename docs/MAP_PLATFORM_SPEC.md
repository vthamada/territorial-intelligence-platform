# MAP_PLATFORM_SPEC
Versao: 1.0.0
Data: 2026-02-13
Escopo: plataforma de mapa do QG para navegacao multi-zoom, camadas territoriais e performance operacional.

## 1) Objetivo

Entregar uma plataforma de mapa dominante para decisao executiva, com:
1. render estavel e fluido para municipio/distrito/setor.
2. troca automatica de camadas por zoom.
3. suporte a camadas tematicas (choropleth, pontos, heatmap, hotspots).
4. contrato de API e cache previsiveis.

## 2) Fora de escopo (v0.1)

1. edicao geoespacial pelo usuario.
2. analise 3D.
3. roteamento/isochrone em tempo real.
4. camadas privadas com ACL complexa.

## 3) Estado atual

### Implementado (MP-1 concluido)

1. `GET /v1/map/layers` — manifesto de 3 camadas (municipality, district, census_sector) com `is_official`, zoom ranges, `fallback_endpoint`. Implementado em `src/app/api/routes_map.py`.
2. `GET /v1/map/style-metadata` — paleta de severidade (critical/attention/stable), paleta por dominio (saude/educacao/trabalho/financas/eleitorado), 4 ranges de legenda, modo padrao choropleth.
3. `GET /v1/geo/choropleth` — render choropleth GeoJSON ativo como fallback primario.
4. Exportacoes CSV/SVG/PNG implementadas no frontend.
5. Cache HTTP ativo para ambos endpoints de manifesto (TTL 1h) via `CacheMiddleware`.
6. Testes E2E cobrindo fluxo completo map layers → style-metadata → render.

### Entregue (MP-2 / MP-3 baseline)

1. ✅ Endpoint MVT de tiles vetoriais (`/v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`).
2. ✅ Troca automatica de camada por zoom no frontend.
3. ✅ `QgMapPage` migrado para engine vetorial progressiva com fallback.
4. ✅ Modos coropletico/pontos/heatmap/hotspots ativos no fluxo vetorial.

## 4) Arquitetura alvo

## 4.1 Camadas de dados

1. `silver.dim_territory` como base de geometria e hierarquia.
2. views/materializacoes por nivel:
   - `map.territory_municipality`
   - `map.territory_district`
   - `map.territory_census_sector`
3. simplificacao de geometria por zoom para reduzir payload.

## 4.2 Servico de tiles

1. endpoint de tiles vetoriais (MVT):
   - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`
2. endpoint de manifesto de camadas:
   - `GET /v1/map/layers`
3. endpoint de metadata de estilo basico:
   - `GET /v1/map/style-metadata`

## 4.3 Frontend

1. migrar pagina `QgMapPage` para engine vetorial progressiva.
2. aplicar estrategia de fallback:
   - preferencial: MVT
   - fallback: choropleth atual

## 5) Regras de zoom e camada

| Faixa de zoom | Camada principal | Camadas auxiliares |
|---|---|---|
| z 0-8 | municipio | hotspots agregados |
| z 9-11 | distrito | pontos de servico agregados |
| z >=12 | setor censitario | pontos de servico detalhados e eleitorais |

Regra:
1. troca de camada deve ser automatica e sem flicker visivel.
2. filtros ativos (indicador, periodo, dominio) devem permanecer ao trocar zoom.

## 6) Modos de visualizacao

1. Choropleth (obrigatorio v1).
2. Pontos proporcionais (obrigatorio v1).
3. Heatmap (obrigatorio v1).
4. Hotspots (obrigatorio v1).
5. Split view comparativo (pos-v1).
6. Time slider (pos-v1).

## 7) Contratos de API (v1)

## 7.1 GET /v1/map/layers

Resposta esperada:
1. lista de camadas com `id`, `label`, `territory_level`, `is_official`, `source`, `default_visibility`.
2. faixas de zoom recomendadas (`zoom_min`, `zoom_max`).

## 7.2 GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt

Regras:
1. retorno `application/vnd.mapbox-vector-tile`.
2. suporte a filtros por query string:
   - `metric`
   - `period`
   - `domain`
   - `only_critical`
3. incluir headers de cache (`ETag`, `Cache-Control`).

## 7.3 GET /v1/map/style-metadata

Resposta:
1. paletas por severidade e dominio.
2. ranges de legenda.
3. metadados de atualizacao e cobertura.

## 8) Performance e SLO

Metas de homologacao:
1. p95 da API de tiles <= 400ms para camada municipal/distrital.
2. p95 da API de tiles <= 700ms para setor censitario.
3. render inicial da Home com mapa <= 3s.
4. troca de zoom percebida <= 300ms sem congelamento da UI.

## 9) Observabilidade

1. telemetria frontend por evento:
   - `map_layer_changed`
   - `map_zoom_changed`
   - `map_mode_changed`
   - `map_tile_error`
2. metricas backend:
   - latencia por endpoint de tile
   - taxa de erro por camada
   - hit ratio de cache

## 10) Plano de implementacao

## Fase MP-1 (CONCLUIDO)
1. ✅ criar manifesto de camadas (`/v1/map/layers`) — `routes_map.py`.
2. ✅ definir regra de zoom e paleta — `style-metadata` com 3 paletas.
3. ✅ manter render atual como fallback — `fallback_endpoint` no manifesto.
4. ✅ cache HTTP para endpoints estaticos — `CacheMiddleware` 1h TTL.
5. ✅ testes E2E e de contrato.

## Fase MP-2 (CONCLUIDO)
1. ✅ endpoint MVT por camada/nivel implementado.
2. ✅ cache HTTP e ETag para tiles habilitados.
3. ✅ metricas de latencia e erro por tile publicadas.

## Fase MP-3 (CONCLUIDO v1)
1. ✅ `QgMapPage` migrado para engine vetorial.
2. ✅ modos coropletico + pontos + heatmap + hotspots habilitados.
3. ✅ validacao de performance em homologacao com benchmark operacional.

## 11) Criterios de aceite

### v1.0 (MP-1) — ATENDIDOS
1. ✅ `GET /v1/map/layers` ativo com manifesto de 3 camadas e zoom ranges.
2. ✅ `GET /v1/map/style-metadata` ativo com paletas e ranges de legenda.
3. ✅ Cache HTTP configurado (1h TTL).
4. ✅ Fallback para choropleth operacional.
5. ✅ Testes E2E cobrindo fluxo map → render.

### v2.0 (MP-2/MP-3) — ENTREGUE (baseline)
1. ✅ `GET /v1/map/tiles/...` ativo com testes de contrato.
2. ✅ troca automatica de camada por zoom funcionando no frontend.
3. ✅ modos choropleth/pontos/heatmap/hotspots operacionais.
4. ✅ baseline de latencia monitorada em homologacao.

### Backlog MP pos-v2
1. split view comparativo.
2. time slider.
3. melhoria de UX para experiencia "google maps-like" (controles, painel lateral e exploracao fluida).
