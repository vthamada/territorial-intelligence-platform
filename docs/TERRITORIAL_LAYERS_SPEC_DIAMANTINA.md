# TERRITORIAL_LAYERS_SPEC_DIAMANTINA
Versão: 1.0.0
Data: 2026-02-13
Escopo: definicao das camadas territoriais oficiais e proxies do QG para Diamantina/MG.

## 1) Objetivo

Padronizar camadas territoriais para garantir:
1. joins consistentes entre dados administrativos, eleitorais e de servicos.
2. transparencia entre camada oficial e camada proxy.
3. rastreabilidade por fonte, cobertura e atualizacao.

## 2) Principios

1. camada oficial tem precedencia sobre proxy.
2. proxy so e usado quando inexistir camada oficial viavel.
3. cada camada deve declarar `official_status`.
4. todo dado exibido no mapa deve carregar metadata de origem.

## 3) Modelo de camadas

## 3.1 Administrativas

1. município (oficial).
2. distrito (oficial).
3. bairro (oficial quando disponível; caso contrario proxy).
4. setor censitario (oficial quando disponível no recorte).

## 3.2 Eleitorais

1. zona eleitoral (oficial agregado).
2. secao eleitoral (agregado; geometria normalmente proxy ou ponto).
3. local de votacao (ponto; geocodificado quando endereco existir).

## 3.3 Servicos e infraestrutura

1. escolas (pontos).
2. unidades de saude (pontos).
3. assistencia social (pontos, quando fonte disponível).
4. conectividade, energia, hidrologia, ambiente (camada territorial agregada).

## 4) Taxonomia oficial vs proxy

Campos obrigatorios por camada:
1. `layer_id`
2. `territory_level`
3. `official_status` (`official`, `proxy`, `hybrid`)
4. `proxy_method` (nulo para official)
5. `source`
6. `dataset`
7. `last_updated_at`
8. `quality_flag`

Regra de UI:
1. toda camada `proxy` ou `hybrid` deve mostrar badge visivel.
2. tooltip e painel lateral devem exibir método de proxy.

## 5) Proxies permitidos (v1)

1. bairro operacional por agrupamento de setores censitarios.
2. secao eleitoral por aproximacao espacial a pontos de local de votacao.
3. poligonos derivados (ex.: Voronoi) somente com disclaimer explicito.

Proxies proibidos:
1. inferencia individual de eleitor.
2. reconstrucoes sem metodologia auditavel.

## 6) Regras de etica e privacidade

1. operar apenas com dados agregados.
2. aplicar supressao de exibição em granularidade fina quando volume < limiar definido.
3. nunca exibir dado que permita reidentificacao individual.
4. manter trilha de auditoria de fonte e método de agregação.

## 7) Contratos de API recomendados

## 7.1 GET /v1/territory/layers/catalog

Retorna catálogo de camadas com:
1. `layer_id`, `label`, `official_status`, `territory_level`.
2. `source`, `dataset`, `coverage`, `last_updated_at`.
3. `proxy_method` quando aplicavel.

## 7.2 GET /v1/territory/layers/{layer_id}/metadata

Retorna:
1. metodologia de construcao da camada.
2. limitacoes conhecidas.
3. qualidade/flags.

## 8) Qualidade e validação

Checks mínimos por camada:
1. cobertura territorial minima esperada.
2. integridade de chave territorial.
3. geometria valida (quando houver poligono).
4. taxa de nulos abaixo do threshold acordado.

## 9) Plano de implementação

## Fase TL-1 (CONCLUIDO)
1. ✅ publicar catálogo de camadas com `is_official` — `GET /v1/map/layers` retorna 3 camadas com flag.
2. ✅ padronizar metadados de camada nos endpoints QG — `coverage_note` presente em payloads de prioridade/territory.
3. ✅ badge de classificação de fonte no frontend — `SourceBadge` com icones oficial/proxy.

## Fase TL-2 (CONCLUIDO)
1. ✅ badge oficial/proxy aplicado nas respostas e paineis executivos.
2. ✅ metadata detalhada por camada publicada em:
   - `GET /v1/map/layers/{layer_id}/metadata`
   - `GET /v1/territory/layers/{layer_id}/metadata`

## Fase TL-3 (CONCLUIDO v1)
1. ✅ checks de qualidade por camada habilitados no `quality_suite`:
   - `map_layer_rows_*`
   - `map_layer_geometry_ratio_*`
2. ✅ página técnica de rastreabilidade de camadas consolidada:
   - `GET /v1/territory/layers/readiness`
   - rota frontend `/ops/layers`.

## 10) Critérios de aceite

### v1.0 (TL-1) — ATENDIDOS
1. ✅ Catálogo de camadas ativo com `is_official` consistente em `/v1/map/layers`.
2. ✅ Badge oficial/proxy visivel no frontend (mapa e paineis).
3. ✅ `coverage_note` presente nos payloads QG.

### v2.0 (TL-2/TL-3) — ENTREGUE (baseline)
1. ✅ UI/API exibem official/proxy e método de proxy por camada.
2. ✅ Metodologia e limitacoes por camada acessiveis via metadata de camada.
3. ✅ Checks de qualidade por camada registrados no fluxo do `quality_suite`.
4. ✅ Rastreabilidade técnica de camadas operacional em `/ops/layers`.

### Backlog TL pós-v2
1. incorporar `local_votacao` com uso completo na UX executiva
   (camada backend `territory_polling_place` ja publicada; falta toggle e fluxo orientado no frontend).
2. adicionar alertas de readiness por camada (degradação automatica) no hub técnico.
