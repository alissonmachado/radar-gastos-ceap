# Modeling — CEAP (CRISP-DM)

**Script:** `src/model.py`
**Insumos:** `data/processed/despesas_limpas.parquet`,
`data/processed/gasto_deputado_categoria_mes.csv`
**Saídas:** `outliers_categoria_pares.csv`, `concentracao_fornecedor.csv`,
`picos_temporais.csv` (todos em `data/processed/`)

## Método

Três detectores estatísticos independentes, todos baseados em **mediana +
MAD** (desvio absoluto mediano) em vez de média/desvio padrão clássicos —
escolha deliberada por ser menos sensível às caudas longas já observadas nos
dados (ex.: fretamento de aeronaves, passagens).

```python
def robust_z(x):
    mediana = x.median()
    mad = (x - mediana).abs().median()
    escala = mad if mad > 0 else 1e-6 * (abs(mediana) + 1)
    return 0.6745 * (x - mediana) / escala
```

Threshold padrão de flag: `|score| > 3.5` (regra de Iglewicz & Hoaglin para
modified z-score).

## 1. Outliers por categoria × mês vs. pares

Compara o gasto mensal de um deputado numa categoria contra outros
deputados na mesma categoria/mês.

- 314 grupos (categoria × ano × mês) avaliados.
- 91 registros pulados por peer group pequeno (< 5 deputados).
- **1.296 flags** (score robusto > 3,5).
- Achado mais forte: contas de liderança partidária (PT, União Brasil) em
  "Fornecimento de Alimentação do Parlamentar", muito acima de deputados
  individuais na mesma categoria/mês.

## 2. Concentração em fornecedor único (HHI)

Por deputado, considerando só despesas com `fornecedor_identificado=True`:
`HHI = Σ(share_fornecedor²)`. Exige mínimo R$ 1.000 em gasto identificado.

- 596 deputados avaliados.
- **141 flags** (HHI > 0,25 — concentração moderada/alta).
- Casos extremos com HHI = 1,0 (100% do gasto identificado em um único
  fornecedor): Aline Gurgel, Ivan Junior, Cristiano Furlan, Liderança do
  Podemos.

## 3. Picos pontuais no tempo (histórico próprio)

Por deputado, compara cada mês contra o próprio histórico (não contra
pares). Exige mínimo 6 meses de histórico.

- 544 deputados avaliados (57 pulados por histórico curto).
- **582 flags**, incluindo tanto picos (Paulo Magalhães, dez/2025, R$ 156
  mil) quanto quedas atípicas (Jorge Braz, jul/2026, R$ 270 — score
  negativo).

## Verificação

Validação manual de um outlier de topo: Arthur Lira, "Passagem Aérea -
Reembolso", mar/2025, R$ 81.639,70 (score 69,66). Conferido contra
`despesas_limpas.parquet`: o valor corresponde exatamente a dois lançamentos
reais (A Star Alliance Member R$ 38.761,90 + LATAM R$ 42.877,80) — nenhum
artefato de agregação.

## Limitações

- O threshold 3,5 é uma convenção estatística, não uma calibração feita
  contra dados rotulados (não há ground-truth) — ver análise de
  sensibilidade em `reports/evaluation.md`.
- Contas de liderança partidária distorcem a comparação por pares (detector
  1), pois têm padrão de gasto estruturalmente diferente de um deputado
  individual.
- 2026 é ano parcial (7 meses); deputados com poucos meses de histórico
  ficam de fora do detector 3 (57 pulados).
