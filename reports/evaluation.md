# Evaluation — CEAP (CRISP-DM)

**Script:** `src/evaluate.py`
**Insumos:** `outliers_categoria_pares.csv`, `picos_temporais.csv`,
`concentracao_fornecedor.csv` (saídas de `src/model.py`, reaproveitadas sem
recálculo)
**Saídas:** `triangulacao_deputados.csv`, `amostra_revisao_manual.csv`

Sem rótulo/ground-truth disponível e sem etapa de LLM (decisão tomada na
fase de Modeling), a avaliação usa três mecanismos indiretos de confiança.

## 1. Sensibilidade a limiares

Recontagem de flags variando o threshold sobre as colunas `score`/`hhi` já
calculadas — sem recalcular os detectores:

| Detector | threshold baixo | padrão | threshold alto |
|---|---:|---:|---:|
| Categoria × pares (score) | 3,0 → 1.785 | 3,5 → 1.296 | 4,0 → 1.004 |
| Pico temporal (score) | 3,0 → 770 | 3,5 → 582 | 4,0 → 457 |
| Concentração fornecedor (HHI) | 0,15 → 326 | 0,25 → 141 | 0,35 → 71 |

A contagem cai de forma monotônica e gradual em todos os detectores — não
há "salto" abrupto perto do limiar padrão, o que indica que a escolha de
3,5/0,25 não é um ponto artificialmente sensível.

## 2. Triangulação por deputado

Consolidação por deputado de quantos dos 3 detectores o sinalizaram pelo
menos uma vez:

- 601 deputados aparecem em ao menos 1 detector.
- **253 sinalizados por 2 ou mais métodos distintos** (maior confiança).
- **26 sinalizados pelos 3 métodos simultaneamente** (prioridade máxima —
  lista completa em `reports/relatorio_final.md` e
  `reports/lista_priorizada.csv`).

A lógica: um outlier confirmado por métodos matematicamente independentes
(comparação com pares, comparação com o próprio histórico, e concentração de
fornecedor) tem menor chance de ser um artefato estatístico de um único
método.

## 3. Amostra para revisão manual

Como não há forma automática de medir precisão sem rótulo humano, foi
gerada uma amostra reprodutível (`random_state=42`) para rotulagem manual
futura:

- 25 casos de `outliers_categoria_pares` (15 flagados + 10 controle)
- 25 casos de `picos_temporais` (15 flagados + 10 controle)
- 15 casos de `concentracao_fornecedor` (10 flagados + 5 controle)
- **Total: 65 linhas**, colunas `rotulo_manual` e `comentario` deixadas
  vazias em `data/processed/amostra_revisao_manual.csv`.

**Status atual: rótulos ainda não preenchidos.** Enquanto isso não for
feito, não é possível calcular taxa de falso positivo/precisão do método —
os três mecanismos acima (sensibilidade, triangulação, amostra) são
substitutos parciais, não uma validação estatística completa.

## Limitações

- Nenhuma métrica de precisão/revocação existe hoje — depende do
  preenchimento manual da amostra.
- A análise de sensibilidade mostra estabilidade de *volume*, não de
  *qualidade* dos casos sinalizados (um detector pode ser estável e ainda
  assim sinalizar majoritariamente falsos positivos).
- A triangulação assume que os 3 métodos são independentes o suficiente
  para que a convergência seja informativa; na prática, categorias como
  "Divulgação da Atividade Parlamentar" aparecem tanto no detector de
  categoria×pares quanto no de pico temporal para os mesmos casos, o que
  reduz um pouco essa independência.
