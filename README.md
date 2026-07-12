# Radar de Gastos da Cota Parlamentar (CEAP)

Pipeline CRISP-DM que prioriza — nunca acusa — despesas atípicas da Cota
Parlamentar (CEAP) usando detecção estatística robusta e triagem por LLM
com saída estruturada e validação humana.

## Contexto

Trabalho final da disciplina **AI Applications**, MBA em **AI for Business**
— Professor Vítor Wilher (Análise Macro). Autor: **Alisson Machado Sousa**.

## Mapa do CRISP-DM

Cada fase tem código versionado em `src/` e um relatório correspondente em
`reports/`:

| # | Fase | Relatório | Script |
|---|---|---|---|
| 1 | Entendimento do Negócio | [`reports/business_understanding.md`](reports/business_understanding.md) | — |
| 2 | Entendimento dos Dados | [`reports/data_understanding.md`](reports/data_understanding.md) | `src/explore.py` |
| 3 | Preparação dos Dados | [`reports/data_preparation.md`](reports/data_preparation.md) | `src/prepare.py` |
| 4 | Modelagem | [`reports/modeling.md`](reports/modeling.md) | `src/model.py`, `src/rubric_prelabel.py`, `src/llm_triage.py` |
| 5 | Avaliação | [`reports/evaluation.md`](reports/evaluation.md), [`reports/evaluation_llm.md`](reports/evaluation_llm.md), [`reports/criterio_rotulagem.md`](reports/criterio_rotulagem.md) | `src/evaluate.py`, `src/evaluate_llm.py` |
| 6 | Implantação | [`reports/relatorio_final.md`](reports/relatorio_final.md), [`reports/paper/trabalho_final.pdf`](reports/paper/trabalho_final.pdf) | `src/deploy.py` |

Documentação de apoio: [`reports/revisao_literatura.md`](reports/revisao_literatura.md)
(citações usadas no paper) e [`referencias.bib`](referencias.bib).

## Resultados-chave

- **284.845 despesas** analisadas (jan/2025–jul/2026), R$ 345.090.001,79.
- **253 deputados** (de 601) sinalizados por 2 ou mais dos 3 detectores
  estatísticos independentes; **26** pelos 3 simultaneamente.
- Avaliação do LLM contra rotulagem humana genuína (n=50): **kappa de Cohen
  = 0,231**, acurácia 40%. O achado central: o LLM **colapsa** para
  severidade "média" em 70% dos casos e categoria "combinação" em 84%,
  quase independentemente do sinal real — um viés sistemático, não ruído.
  Ver [`reports/evaluation_llm.md`](reports/evaluation_llm.md) e a seção
  Avaliação do [paper](reports/paper/trabalho_final.pdf).
- Custo de classificação por LLM: **US$ 0,00525 por caso** (medido via API
  de contagem de tokens, não estimado) — ver
  [`reports/custo_llm_triage.json`](reports/custo_llm_triage.json).

## Estrutura

```
data/raw/          downloads originais (Ano-2025.csv, Ano-2026.csv) — gerado localmente, fora do git
data/processed/     dados intermediários de cada fase — gerado localmente, fora do git
src/                pipeline, uma etapa por script
notebooks/          exploração pontual
reports/            relatórios de cada fase + lista priorizada (versionados no git)
reports/paper/      relatório técnico final em Quarto + LaTeX (PDF)
.claude/skills/      skills do Claude Code usadas neste projeto (setup-am, paper-analise-macro)
```

## Como reproduzir do zero

```bash
# 1. Ambiente
python -m venv .venv
.venv\Scripts\activate          # Windows; no Linux/Mac: source .venv/bin/activate
pip install pandas pyarrow jupyter pyyaml matplotlib anthropic python-dotenv pydantic

# 2. Chave de API (nunca commitada — .env está no .gitignore)
cp .env.example .env
# edite .env e cole sua ANTHROPIC_API_KEY

# 3. Dados brutos — baixe e descompacte em data/raw/
#    https://www.camara.leg.br/cotas/Ano-2025.csv.zip
#    https://www.camara.leg.br/cotas/Ano-2026.csv.zip

# 4. Pipeline, na ordem das fases do CRISP-DM
python src/explore.py              # Data Understanding
python src/prepare.py              # Data Preparation
python src/model.py                # Modeling — 3 detectores estatísticos
python src/rubric_prelabel.py      # Modeling — baseline determinístico (não-LLM)
python src/evaluate.py             # Evaluation — sensibilidade, triangulação
python src/deploy.py               # Deployment — lista priorizada final
python src/llm_triage.py --top 50  # Modeling — classificação por LLM (saída estruturada, custa ~US$0,26 para 50 casos)
python src/estimate_llm_cost.py    # Evaluation — custo real de tokens (count_tokens, gratuito)
python src/evaluate_llm.py         # Evaluation — concordância LLM vs. rubrica e vs. humano

# 5. Relatório final em PDF
cd reports/paper
quarto render trabalho_final.qmd --to pdf
```

`src/rotulos_humanos.csv` contém rotulagem humana genuína já preenchida
neste repositório (não é regenerada por script) — ver a metodologia em duas
etapas e a distinção com a rubrica automática em
[`reports/criterio_rotulagem.md`](reports/criterio_rotulagem.md).

## Metodologia (resumo)

Três detectores estatísticos independentes (mediana + MAD, "score robusto",
menos sensível a valores extremos que média/desvio padrão comuns):

1. **Categoria × pares**: gasto mensal de um deputado numa categoria vs.
   outros deputados na mesma categoria/mês.
2. **Concentração de fornecedor (HHI)**: quanto do gasto de um deputado está
   concentrado num único fornecedor.
3. **Pico temporal**: meses que fogem do padrão histórico do próprio deputado.

Um deputado sinalizado por 2 ou mais métodos distintos entra na lista
priorizada. Os casos priorizados são então classificados por um LLM (Claude,
saída estruturada via Pydantic) para severidade e explicação em linguagem
cidadã — nunca para decidir sozinho o que é atípico.

## Decisões de projeto e aprendizados

Registro aqui, em primeira pessoa, algumas decisões que moldaram o que este
pipeline faz e não faz — e um erro que encontrei no caminho.

**Por que CEAP e não DataSUS/FNS.** Cheguei a considerar repasses de saúde
(DataSUS/FNS) como domínio do trabalho — volume comparável, mesmo tipo de
problema. Escolhi CEAP porque os arquivos anuais da Câmara já vêm num
formato único e estável (`Ano-{ano}.csv.zip`), enquanto dados de saúde
exigiriam integrar múltiplas fontes antes de qualquer análise. Com o prazo
do trabalho final, troquei profundidade de exploração por entregar um
pipeline completo, do dado bruto ao paper.

**Por que mediana + MAD e não um modelo de machine learning.** Descartei
deliberadamente abordagens de ML (ex.: isolation forest, clustering) para
detectar outliers. Num domínio em que o resultado associa nomes de pessoas
públicas a um ranking de atenção, um método que eu não consigo explicar em
uma frase para um jornalista ou auditor não serve — mesmo que tivesse
desempenho melhor em alguma métrica. Mediana e MAD são conferíveis à mão.

**"O LLM nunca acusa" é uma decisão de design, não uma limitação técnica.**
O LLM não decide o que é atípico — isso já foi apurado estatisticamente
antes de qualquer prompt. Ele só classifica severidade e explica em
linguagem simples, com uma regra absoluta no *system prompt*
(`src/llm_triage.py`) proibindo qualquer insinuação de irregularidade. O
custo de um falso positivo aqui não é um erro de classificação qualquer —
é o nome de uma pessoa associado a uma acusação que ela nunca cometeu.

**O bug dos 14 dígitos do CNPJ.** Na fase de exploração, minha primeira
implementação do filtro de "CNPJ genérico" comparava contra códigos de 12
dígitos, não 14 — resultado: zero registros encontrados, quando na verdade
existem 8.527. Só percebi o erro porque um resultado zero era suspeito
demais para aceitar sem checar. A correção está registrada em
`reports/data_understanding.md`.

**A rotulagem em duas passadas e o caso Bruno Ganem.** Rotulei os 50 casos
de avaliação olhando só o sinal de categoria×pares, sem o valor de pico —
um critério mais restrito do que a rubrica pedia. Ao perceber a diferença,
revisei os 2 casos em que isso mudava o resultado (ver
`reports/criterio_rotulagem.md`). Um deles, Bruno Ganem, é um caso de
fronteira real: o valor do pico justificaria "alta" pela regra mecânica,
mas a concentração em fornecedor de anúncios no Facebook é um padrão comum
de campanha de divulgação parlamentar. Optei por manter "média" — um
julgamento que registrei como decisão minha, não como resultado do
algoritmo.

**O principal aprendizado: o LLM colapsa para respostas seguras.** Antes de
rodar a avaliação, eu esperava que divergências entre LLM e rotulagem
humana fossem majoritariamente ruído. Não foram: o LLM classificou "média"
em 70% dos 50 casos e "combinação" em 84%, quase independentemente do caso
real — kappa de 0,231, concordância "razoável", não "substancial" (Landis &
Koch, 1977). Isso muda a próxima iteração do projeto: o problema não é
falta de dados de treino nem um detalhe qualquer de prompt, é o LLM
convergindo para a opção que raramente está claramente errada. A correção
que proponho — injetar os limiares da rubrica no prompt — ataca essa causa
específica, não um sintoma genérico de "melhorar o prompt".

## Relatório técnico completo

O paper técnico (Quarto + LaTeX, todas as 6 fases do CRISP-DM) está em
[`reports/paper/trabalho_final.pdf`](reports/paper/trabalho_final.pdf)
(fonte: [`reports/paper/trabalho_final.qmd`](reports/paper/trabalho_final.qmd)).
Versão em inglês (mesmo pipeline, mesmos números, tradução integral):
[`reports/paper/trabalho_final_en.pdf`](reports/paper/trabalho_final_en.pdf)
(fonte: [`reports/paper/trabalho_final_en.qmd`](reports/paper/trabalho_final_en.qmd)).
