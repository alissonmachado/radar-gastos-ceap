# Business Understanding — Radar de Gastos da Cota Parlamentar (CEAP)

## Problema

A Câmara dos Deputados publica diariamente os gastos da Cota para o
Exercício da Atividade Parlamentar (CEAP). No recorte deste projeto
(jan/2025 a jul/2026, 19 meses), isso já soma **284.845 despesas individuais
e R$ 345.090.001,79** — volume humanamente inauditável um lançamento de
cada vez. Sem uma forma de priorizar, qualquer tentativa de fiscalização
manual é inviável: cidadãos, jornalistas e órgãos de controle não têm como
revisar 285 mil linhas para decidir onde vale a pena olhar com mais atenção.

## Público-alvo

- **Cidadãos** interessados em acompanhar o uso da cota por seus
  representantes.
- **Jornalistas** que precisam de pontos de partida concretos para
  reportagens de accountability, sem recomeçar a análise do zero.
- **Auditores / órgãos de controle** que já têm processo de fiscalização,
  mas se beneficiam de uma triagem prévia que aponte onde concentrar
  esforço.

## Objetivo

**Priorizar, não acusar.** O projeto não determina se uma despesa é
irregular — isso exige investigação humana, contexto e contraditório. O que
o pipeline entrega é um ranking estatístico objetivo de casos que fogem do
padrão esperado, para que a atenção limitada de quem fiscaliza seja alocada
de forma mais eficiente.

Este princípio molda todas as decisões técnicas do projeto (ver
`CLAUDE.md`, seção "Regras invioláveis"): nenhum número inventado, nenhuma
classificação de reputação de pessoas, e transparência sobre as limitações
de cada achado.

## Critérios de sucesso

1. **Reprodutibilidade**: pipeline completo (`src/explore.py` →
   `prepare.py` → `model.py` → `evaluate.py` → `deploy.py`) roda do zero a
   partir dos dados brutos publicados pela Câmara, com código versionado em
   git — qualquer pessoa pode conferir como cada número foi calculado.
2. **Redução de escopo útil**: das 284.845 despesas e 601 deputados
   analisados, o pipeline reduz o universo de atenção para um conjunto
   gerenciável — 253 deputados sinalizados por 2 ou mais dos 3 métodos
   independentes, e 26 pelos 3 simultaneamente (ver
   `reports/relatorio_final.md`).
3. **Transparência de limitações**: todo achado vem acompanhado das
   ressalvas necessárias (contas de liderança partidária, ano parcial,
   ausência de validação humana) — ver `reports/relatorio_final.md`,
   seção "O que isso NÃO significa".
4. **Caminho para validação futura**: existe um mecanismo concreto
   (`data/processed/amostra_revisao_manual.csv`, 65 casos) para medir, no
   futuro, a taxa de falsos positivos do método por rotulagem manual — sem
   isso, o projeto não teria como evoluir de "prioriza" para "prioriza com
   precisão conhecida".

Este projeto é considerado bem-sucedido se um jornalista ou auditor
conseguir, a partir de `reports/lista_priorizada.csv`, escolher por onde
começar uma investigação em minutos em vez de teria que revisar 285 mil
linhas manualmente.
