# TERRITORIAL_LAYERS_SPEC_DIAMANTINA
Versao: 0.1.0
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

1. municipio (oficial).
2. distrito (oficial).
3. bairro (oficial quando disponivel; caso contrario proxy).
4. setor censitario (oficial quando disponivel no recorte).

## 3.2 Eleitorais

1. zona eleitoral (oficial agregado).
2. secao eleitoral (agregado; geometria normalmente proxy ou ponto).
3. local de votacao (ponto; geocodificado quando endereco existir).

## 3.3 Servicos e infraestrutura

1. escolas (pontos).
2. unidades de saude (pontos).
3. assistencia social (pontos, quando fonte disponivel).
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
2. tooltip e painel lateral devem exibir metodo de proxy.

## 5) Proxies permitidos (v1)

1. bairro operacional por agrupamento de setores censitarios.
2. secao eleitoral por aproximacao espacial a pontos de local de votacao.
3. poligonos derivados (ex.: Voronoi) somente com disclaimer explicito.

Proxies proibidos:
1. inferencia individual de eleitor.
2. reconstrucoes sem metodologia auditavel.

## 6) Regras de etica e privacidade

1. operar apenas com dados agregados.
2. aplicar supressao de exibicao em granularidade fina quando volume < limiar definido.
3. nunca exibir dado que permita reidentificacao individual.
4. manter trilha de auditoria de fonte e metodo de agregacao.

## 7) Contratos de API recomendados

## 7.1 GET /v1/territory/layers/catalog

Retorna catalogo de camadas com:
1. `layer_id`, `label`, `official_status`, `territory_level`.
2. `source`, `dataset`, `coverage`, `last_updated_at`.
3. `proxy_method` quando aplicavel.

## 7.2 GET /v1/territory/layers/{layer_id}/metadata

Retorna:
1. metodologia de construcao da camada.
2. limitacoes conhecidas.
3. qualidade/flags.

## 8) Qualidade e validacao

Checks minimos por camada:
1. cobertura territorial minima esperada.
2. integridade de chave territorial.
3. geometria valida (quando houver poligono).
4. taxa de nulos abaixo do threshold acordado.

## 9) Plano de implementacao

## Fase TL-1
1. publicar catalogo de camadas com status official/proxy.
2. padronizar metadados de camada nos endpoints QG.

## Fase TL-2
1. implementar badge oficial/proxy em mapa e painois.
2. publicar metadata detalhada por camada.

## Fase TL-3
1. habilitar checks de qualidade por camada no `quality_suite`.
2. consolidar pagina tecnica de rastreabilidade de camadas no `/admin`.

## 10) Criterios de aceite

1. catalogo de camadas ativo com `official_status` consistente.
2. UI exibe claramente official/proxy em mapa e detalhes.
3. metodologia e limitacoes por camada acessiveis via API.
4. checks de qualidade por camada registrados em `ops.pipeline_checks`.
