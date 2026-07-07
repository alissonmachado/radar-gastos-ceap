# Radar de Gastos Parlamentares (CEAP) — Trabalho Final MBA em Artificial Intelligence for Business referente a materia AI Applications

## Contexto

Projeto individual CRISP-DM sobre os gastos da Cota para o Exercício da
Atividade Parlamentar (CEAP) da Câmara dos Deputados. Objetivo: priorizar,
entre ~285 mil despesas (R$ 345 milhões, jan/2025 a jul/2026), os padrões de
gasto atípicos que merecem atenção de cidadãos, jornalistas e auditores. A
detecção de anomalias é estatística (ver `src/model.py`); o projeto nunca
julga reputação de pessoas nem afirma irregularidade — apenas prioriza casos
para investigação humana.

## Regras invioláveis

1. **Nenhum número inventado**: todo valor citado em relatório/slide sai de
   código deste repositório, reproduzível a partir dos dados brutos.
2. **Chaves de API somente em `.env`** (já no `.gitignore`). Nunca
   hardcoded, nunca commitadas. Hoje o projeto não usa nenhuma API de LLM —
   quando `llm_triage.py` for criado, a chave (`ANTHROPIC_API_KEY`) segue
   essa regra.
3. **O LLM nunca julga reputação de pessoas.** Quando existir (ver
   "a criar" abaixo), ele analisa padrões numéricos já detectados
   estatisticamente e apenas classifica/explica com saída estruturada
   (Pydantic) — nunca decide sozinho o que é uma anomalia.
4. **Toda saída de LLM é validada contra schema Pydantic**; falha de
   validação = retry com feedback, máx. 2 tentativas, depois marca o
   registro como "não classificado".
5. **Um commit por unidade de trabalho concluída**, mensagem no padrão
   "fase: descrição" (ex.: "modeling: detecção de outliers robusta CEAP").

## Dados — peculiaridades já mapeadas (ver `reports/data_understanding.md`)

- Fonte: arquivos anuais CEAP em `https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip`
  (CSV, separador `;`, UTF-8 com BOM, atualização diária). Anos usados: 2025
  e 2026 (parcial, até julho).
- 284.845 linhas, 33 colunas nos dados brutos. **Valor de referência é
  sempre `vlrLiquido`** (líquido de glosa), nunca `vlrDocumento` (bruto) —
  usar o bruto infla artificialmente os totais.
- **7.191 registros com `vlrLiquido` negativo** (estornos/compensações):
  mantidos no dataset limpo com flag `flag_estorno`, somam corretamente no
  total gasto.
- **8.527 registros com CNPJ genérico** (`00000000000001`, `...02`, `...06`
  — 14 dígitos, sem fornecedor identificável) + 37.108 com CNPJ ausente =
  45.635 registros com `fornecedor_identificado=False`: mantidos nas somas
  por deputado/categoria, mas **excluídos do cálculo de concentração de
  fornecedor (HHI)** em `src/model.py`.
- Comparações de gasto **sempre por categoria** (`txtDescricao`) e período,
  nunca pelo total bruto — categorias têm padrões de uso muito diferentes
  entre si (ex.: "Divulgação da Atividade Parlamentar" concentra ~44% do
  gasto total; comparar um deputado nessa categoria com a média geral não
  faz sentido).
- Contas de liderança partidária (`LID.GOV-CD` etc., ~0,48% das linhas) têm
  padrão de gasto diferente de deputados individuais — distorcem
  comparações "por pares" quando aparecem no mesmo grupo categoria×mês.

## Arquitetura atual (real)

```
data/raw/        downloads originais (fora do git)
data/processed/  csv/parquet intermediários de cada fase (fora do git)
src/
  explore.py     Data Understanding — perfil, nulos, tipos, top 10s
  prepare.py     Data Preparation  — limpeza, tipagem, flags, agregações
  model.py       Modeling          — 3 detectores estatísticos (robusto MAD)
  evaluate.py    Evaluation        — sensibilidade, triangulação, amostra manual
  deploy.py      Deployment        — lista priorizada final
  llm_triage.py  A CRIAR — única etapa que ainda não existe. Quando
                 implementada: recebe os casos já sinalizados por
                 model.py/evaluate.py, classifica/explica via API Anthropic
                 com saída Pydantic (regras 3 e 4 acima), nunca decide
                 sozinha o que é anômalo.
notebooks/       exploração pontual
reports/         relatórios de cada fase + lista priorizada (git-tracked)
.env             ANTHROPIC_API_KEY (quando llm_triage.py existir)
```

Hoje **não há nenhuma chamada de LLM no projeto** — as três detecções de
`model.py` são puramente estatísticas (mediana + MAD, "score robusto",
threshold 3,5; HHI para concentração de fornecedor, threshold 0,25). O
`motivo_resumo` gerado em `deploy.py` é template Python (f-string), não LLM.

## Stack e convenções

- Python 3.12, pandas, pyarrow (para parquet).
- Windows: sempre `sys.stdout.reconfigure(encoding="utf-8")` em scripts com
  prints acentuados.
- Scripts idempotentes: rodar duas vezes não duplica dados.
- Padrão de código: função `section()` para imprimir cada etapa no console;
  paths sempre via `Path(__file__).resolve().parent.parent`.

## Comandos do pipeline

```bash
pip install pandas pyarrow

python src/explore.py    # Data Understanding
python src/prepare.py    # Data Preparation
python src/model.py      # Modeling
python src/evaluate.py   # Evaluation
python src/deploy.py     # Deployment
# python src/llm_triage.py   # a criar
```
