# Data Preparation — CEAP (CRISP-DM)

**Script:** `src/prepare.py`
**Insumo:** `data/raw/Ano-2025.csv`, `data/raw/Ano-2026.csv` (mesma leitura
de `explore.py`: `sep=";"`, `encoding="utf-8-sig"`)
**Saídas:** `data/processed/despesas_limpas.parquet`,
`data/processed/gasto_deputado_categoria_mes.csv`

## Decisões tomadas

A fase de Data Understanding (`reports/data_understanding.md`) identificou
três problemas de qualidade. Para cada um, a decisão foi **sinalizar sem
excluir**, preservando os totais de gasto reais:

| Problema | Decisão | Motivo |
|---|---|---|
| 7.191 registros com `vlrLiquido` negativo | Mantidos + coluna `flag_estorno` | São estornos/compensações reais; excluir alteraria o total gasto |
| 8.527 CNPJs genéricos (`00000000000001/02/06`) + 37.108 CNPJ ausentes | Mantidos + coluna `fornecedor_identificado=False` | Ainda representam gasto real do deputado; só não servem para análise por fornecedor |
| Tipos "crus" (`datEmissao` texto, `txtCNPJCPF` com máscara) | Convertidos, sem remover colunas | Necessário para agregações temporais e comparação de CNPJ |

## Transformações aplicadas

1. **Tipagem**: `datEmissao` → `datetime64` (0 valores viraram `NaT` —
   100% das datas foram parseáveis).
2. **`cnpjcpf_digits`**: nova coluna só com os dígitos de `txtCNPJCPF`
   (reaproveita `cnpj_digits()` de `explore.py`).
3. **`periodo`**: nova coluna `YYYY-MM` a partir de `numAno`/`numMes`, para
   facilitar agregações temporais nas fases seguintes.
4. **`flag_estorno`**: `vlrLiquido < 0` → **7.191 registros = True**.
5. **`fornecedor_identificado`**: `False` quando `cnpjcpf_digits` está nos
   códigos genéricos (`00000000000001` a `...07`) ou está ausente:
   - CNPJ genérico: 8.527
   - CNPJ ausente: 37.108
   - **Total `fornecedor_identificado=False`: 45.635 registros (16,0%)**

## Verificação

- **Nenhuma linha removida**: 284.845 linhas antes e depois da limpeza
  (checado via `assert` no próprio script).
- Dataset limpo salvo em `despesas_limpas.parquet` — 284.845 linhas, 37
  colunas, tipos confirmados (`datEmissao` como `datetime64[us]`,
  `flag_estorno`/`fornecedor_identificado` como `bool`).
- Agregado `gasto_deputado_categoria_mes.csv` (deputado × categoria × mês):
  **50.176 linhas**, com `vlrLiquido_total`, `n_lancamentos` e `n_estornos`
  por grupo — insumo direto para a fase de Modeling.

## Limitações conhecidas

- CNPJ ausente (13,03% das linhas originais) é tratado da mesma forma que
  CNPJ genérico (`fornecedor_identificado=False`), mas são situações
  distintas: um é "sem nota emitida com CNPJ", outro é "código placeholder
  da Câmara". Ambos são excluídos do cálculo de HHI por fornecedor na fase
  de Modeling, mas essa junção pode esconder nuances entre os dois casos.
- Colunas quase 100% nulas (`datPagamentoRestituicao`, `vlrRestituicao`)
  foram mantidas sem tratamento — não há uso previsto para elas nas fases
  seguintes.
