# Visao de Produto e Direcao Visual - Frontend

Data de referencia: 2026-02-11
Escopo: orientar as proximas implementacoes de frontend para evoluir de painel operacional para sistema de inteligencia territorial.

## 1) Visao do produto

O frontend deve evoluir de um painel tecnico de operacao para uma sala de situacao territorial.

Diretriz central:
- Operacao (runs/checks/connectores) continua existindo, mas como camada de sustentacao.
- Inteligencia territorial (mapa, tendencias, comparacoes e perfil municipal) vira camada principal de decisao.

## 2) Direcao visual

1. Mapa como elemento principal da experiencia
- O mapa deve deixar de ser acessorio e passar a ser o ponto de entrada da analise.
- O usuario deve conseguir navegar por indicador, periodo e nivel territorial sem sair da mesma tela.

2. Hierarquia clara de informacao
- Nivel 1: visao executiva (KPI e alertas).
- Nivel 2: mapa e distribuicao territorial.
- Nivel 3: detalhe tabular e operacional.

3. Linguagem visual por dominio
- Saude, educacao, trabalho, seguranca e financas devem ter codificacao visual consistente.
- Cores e rotulos devem reduzir ambiguidade na leitura.

4. Foco em legibilidade e contexto
- Cards com metrica + variacao temporal.
- Tooltips ricos com fonte e data de atualizacao.
- Sempre exibir metadados de frescor para evitar leitura fora de contexto.

## 3) Estrutura de telas alvo

1. Visao Executiva
- KPI multipilar de Diamantina.
- Tendencias recentes e alertas de variacao.
- Atalhos para mapa e perfil territorial.

2. Mapa Territorial
- Coropletico por indicador/periodo/nivel.
- Selecao de territorio no mapa e drill-down quando existir granularidade.
- Legenda de escala e comparacao rapida entre territorios.

3. Perfil do Territorio
- Pagina 360 do territorio selecionado.
- Historico por dominio.
- Comparacao com pares territoriais.

4. Operacao de Dados
- Estado da API, jobs, checks e conectores.
- Diagnostico e troubleshooting (camada tecnica).

## 4) Prioridade de implementacao (proximas iteracoes)

Fase A (alto impacto imediato)
1. Entregar tela de mapa coropletico usando `/v1/geo/choropleth`.
2. Integrar filtros de indicador/periodo/nivel e legenda.
3. Exibir tooltip com nome do territorio, valor e metadata de fonte.

Fase B (consolidacao analitica)
1. Criar visao executiva com KPI e tendencias.
2. Criar perfil territorial com comparativos.
3. Padronizar componentes de estado (loading/empty/error) em todas as telas.

Fase C (hardening final)
1. Testes E2E de navegacao e fluxos criticos.
2. Observabilidade de frontend (erros e web vitals).
3. Refinamento mobile e acessibilidade (teclado, foco, contraste).

## 5) Principios para nao desviar da visao

1. Nenhuma tela nova deve ser somente operacional sem valor analitico territorial.
2. Cada visualizacao deve responder a uma pergunta de decisao (nao apenas exibir dado).
3. Toda metrica deve informar fonte e recencia.
4. Sempre priorizar compreensao de territorio antes de detalhe tecnico.

## 6) Definicao de pronto visual (frontend de inteligencia territorial)

Considera-se pronto quando:
1. Existe visao executiva orientada a decisao.
2. Existe mapa interativo com filtros funcionais e leitura clara.
3. Existe perfil territorial com historico e comparacao.
4. A camada operacional continua disponivel e integrada.
5. Testes e build passam de forma estavel em homologacao.
