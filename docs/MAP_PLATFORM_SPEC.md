# MAP_PLATFORM_SPEC
Versao: 0.1.0
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

1. mapa atual baseado em `GET /v1/geo/choropleth` com render SVG no frontend.
2. exportacoes CSV/SVG/PNG ja implementadas.
3. ainda sem arquitetura MVT e sem gestao de camadas por zoom.

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

## Fase MP-1
1. criar manifesto de camadas (`/v1/map/layers`).
2. definir regra de zoom e paleta.
3. manter render atual como fallback.

## Fase MP-2
1. implementar endpoint MVT por camada/nivel.
2. adicionar cache HTTP e estrategia de invalidacao por periodo.
3. incluir metricas de latencia e erro.

## Fase MP-3
1. migrar `QgMapPage` para engine vetorial.
2. habilitar choropleth + pontos + heatmap + hotspots.
3. validar SLO de performance em homologacao.

## 11) Criterios de aceite

1. `GET /v1/map/layers` e `GET /v1/map/tiles/...` ativos com testes de contrato.
2. troca automatica de camada por zoom funcionando no frontend.
3. modos choropleth/pontos/heatmap/hotspots operacionais.
4. metas de latencia e render atendidas na baseline de homologacao.
