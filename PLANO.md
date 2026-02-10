# Plano de Execução do Projeto

Data de referência: 2026-02-10  
Status: ativo  
Escopo deste arquivo: planejamento, fases, prioridades e sequência de implementação.

## 1) Referências e papéis documentais

- `CONTRATO.md`: requisitos técnicos e critérios finais de aceite (imutável por padrão).
- `PLANO.md`: execução do trabalho (fases, backlog, prioridades, marcos).
- `HANDOFF.md`: estado operacional corrente e próximos passos imediatos.
- `CHANGELOG.md`: histórico de mudanças e evidências de validação.

## 2) Estratégia por ondas (MVP)

MVP-1:
- `ibge_admin_fetch`
- `ibge_geometries_fetch`
- `ibge_indicators_fetch`
- `dbt_build`
- `quality_suite`
- API v1 + observabilidade ops

MVP-2:
- `tse_catalog_discovery`
- `tse_electorate_fetch`
- `tse_results_fetch`

MVP-3:
- `education_inep_fetch`
- `health_datasus_fetch`
- `finance_siconfi_fetch`
- `labor_mte_fetch`

## 3) Plano completo de execução (início ao fim)

## Fase 0 - Preparação e baseline técnico

Objetivo:
- garantir ambiente reproduzível para execução de ponta a ponta.

Atividades:
1. Validar bootstrap completo (venv, dependências, banco e extensões).
2. Rodar inicialização de schema.
3. Executar suíte de testes base.

Critérios de aceite mensuráveis:
1. `python -m pip check` sem conflitos.
2. `pytest -q -p no:cacheprovider` com 100% dos testes da suíte atual aprovados.
3. `python scripts/init_db.py` executa sem erro em banco limpo.

## Fase 1 - Fechamento funcional crítico (P0)

Objetivo:
- concluir `labor_mte_fetch` para operação sem dependência manual recorrente.

Atividades:
1. Fechar estratégia de automação para MTE.
2. Ajustar parsing/seleção de arquivos para reduzir falhas de ingestão.
3. Atualizar runbook e registro de conector.

Critérios de aceite mensuráveis:
1. `labor_mte_fetch` com status `implemented` em `configs/connectors.yml`.
2. 3 execuções consecutivas de `labor_mte_fetch` com `dry_run=False` finalizando `run_status=successful`.
3. Cada execução gera registros em `ops.pipeline_runs` e `ops.pipeline_checks`.

## Fase 2 - Fechamento operacional

Objetivo:
- consolidar execução operacional previsível e observável.

Atividades:
1. Consolidar `dbt_build` no modo `dbt` em ambiente alvo.
2. Expandir checks e thresholds por domínio.
3. Validar endpoints de observabilidade para operação diária.

Critérios de aceite mensuráveis:
1. `DBT_BUILD_MODE=dbt` executa em ambiente alvo sem fallback não planejado.
2. Check crítico ativo para cada tabela crítica definida no contrato.
3. `/v1/ops/summary`, `/v1/ops/timeseries` e `/v1/ops/sla` respondem em ambiente de homologação.
4. SLO-1 e SLO-3 do `CONTRATO.md` atendidos por janela de 7 dias.

## Fase 3 - Release de produção

Objetivo:
- validar ciclo completo em ambiente limpo com evidência formal.

Atividades:
1. Rodar fluxo completo em ambiente limpo.
2. Registrar baseline de regressão.
3. Publicar documentação final de operação backend.

Critérios de aceite mensuráveis:
1. `run_mvp_all` executa sem intervenção manual recorrente.
2. suíte de testes aprovada no mesmo commit de release.
3. evidências publicadas em `CHANGELOG.md` e operação documentada em `HANDOFF.md`.

## Fase 4 - Frontend MVP de operação

Objetivo:
- disponibilizar interface operacional e analítica mínima integrada à API v1.

Atividades:
1. Criar app frontend com stack oficial (`React + Vite + TypeScript`).
2. Implementar shell da aplicação:
   - roteamento (`React Router`)
   - configuração de ambiente (`VITE_API_BASE_URL`)
3. Implementar camada de dados (`TanStack Query`) e cliente API tipado.
4. Implementar telas:
   - saúde operacional
   - execução de pipelines
   - territórios e indicadores
5. Cobrir UI com testes unitários/integração e smoke de navegação.

Critérios de aceite mensuráveis:
1. `npm run build` e `npm test` executam sem erro.
2. Telas críticas exibem estados de `loading`, `empty` e `error` com `request_id`.
3. Filtros e paginação reproduzem contratos dos endpoints `/v1/ops/*`.
4. Frontend publicado em homologação e validado contra API real.

## 4) Backlog priorizado

P0:
1. Fechar `labor_mte_fetch` para `implemented`.
2. Validar release backend em ambiente limpo e reprodutível.

P1:
1. Consolidar `dbt` CLI no ambiente alvo.
2. Expandir qualidade por dataset.
3. Implementar frontend MVP operacional.
4. Publicar build frontend em homologação.

P2:
1. Alertas automáticos por SLA/SLO.
2. Política de retenção Bronze por ambiente.
3. Evoluir frontend para dashboards analíticos avançados.
4. Incluir autenticação/autorização no frontend (se exigência de acesso for ativada).

## 5) Entrega frontend (detalhamento por sprint)

Sprint F1 - Fundação (1 semana):
1. Criar estrutura `frontend/` no repositório.
2. Configurar TypeScript, lint, testes e build.
3. Configurar `React Router` e `TanStack Query`.
4. Implementar cliente API tipado e camada de serviços.

Aceite F1:
1. `npm run build` e `npm test` executam localmente sem erros.
2. Troca de URL da API por variável sem alteração de código.

Sprint F2 - Operação (1 semana):
1. Entregar tela de saúde operacional.
2. Entregar tela de pipelines com filtros e paginação.
3. Entregar feedback completo de erro/carregamento/vazio.

Aceite F2:
1. Operações de monitoramento podem ser feitas sem acesso ao banco.
2. Filtros da UI reproduzem os filtros dos endpoints `/v1/ops/*`.

Sprint F3 - Território e indicadores (1 semana):
1. Entregar consulta de territórios.
2. Entregar consulta de indicadores por período e nível territorial.
3. Ajustar responsividade para notebook e mobile.

Aceite F3:
1. Usuário navega por dados territoriais sem SQL.
2. Build validado em homologação com API real.

Sprint F4 - Hardening (0.5 semana):
1. Ajustar performance inicial (bundle e carregamento).
2. Incluir testes smoke de navegação.
3. Fechar documentação de operação do frontend.

Aceite F4:
1. Frontend apto para operação diária junto com API v1.
2. SLO-2 do `CONTRATO.md` monitorado em homologação.

## 6) Riscos principais e mitigação

1. Dependência externa de fontes públicas (instabilidade/portal bloqueado):
- mitigação: fallback controlado, retry, e monitoramento de falha por conector.

2. Divergência entre contrato e implementação:
- mitigação: revisão de PR obrigatória com checagem de aderência a `CONTRATO.md`.

3. Atraso na entrega do frontend:
- mitigação: sprints curtos, escopo MVP rígido e validação incremental por tela.

4. Regressão de qualidade:
- mitigação: thresholds versionados e testes automatizados por domínio.

## 7) Governança do plano

1. Este arquivo deve refletir somente execução e priorização.
2. Números de status corrente (percentual, testes passados, estado do dia) não devem ser mantidos aqui.
3. Atualizar `HANDOFF.md` a cada ciclo com estado atual e próximos passos.
4. Atualizar `CHANGELOG.md` com evidências objetivas de validação e mudanças implementadas.
