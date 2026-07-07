# Critério de Pré-Rotulagem por Rubrica — CEAP

**Script:** `src/rubric_prelabel.py`
**Insumos:** `reports/lista_priorizada.csv` (50 primeiros casos),
`data/processed/outliers_categoria_pares.csv`,
`data/processed/picos_temporais.csv`,
`data/processed/concentracao_fornecedor.csv`
**Saída:** `reports/rotulos_prelabel.csv`

## Por que existe

Antes de comparar o LLM (`reports/triage_llm.csv`) contra rotulagem humana,
é útil ter um terceiro ponto de referência **determinístico** (sem
subjetividade, sem custo de API): uma rubrica fixa aplicada sobre os mesmos
sinais estatísticos já calculados em Modeling/Evaluation. Isso não substitui
o rótulo humano — é um rascunho auditável para acelerar a revisão, com
colunas `severidade_humana`/`categoria_humana` propositalmente vazias.

## Regra de severidade

```
alta  se sinal_principal >= R$ 50.000
      OU hhi >= 0,5
      OU (n_flags_categoria_pares + n_flags_pico_temporal) >= 5

baixa se sinal_principal < R$ 10.000
      OU fornecedor concentrado contém "Facebook"
      OU o único pico temporal é uma queda em 06/2026 ou 07/2026 (mês parcial)

media caso contrário
```

**Precedência**: a condição "alta" é checada primeiro; "baixa" só se aplica
se nenhuma condição de "alta" foi satisfeita. Isso é uma escolha de
implementação (a rubrica original não especifica o que fazer se ambas as
condições batessem ao mesmo tempo) — na prática, poucos casos têm sinal
grande *e* fornecedor Facebook *e* queda de mês parcial simultaneamente.

**"Sinal principal"** = o maior valor em R$ entre o caso mais atípico do
deputado no detector de categoria×pares e no detector de pico temporal
(mesma lógica de `maior_caso`/`montar_motivo` em `src/deploy.py`). Não
inclui HHI, que é tratado como condição separada (é um índice 0–1, não um
valor monetário).

**"Único pico em mês parcial"**: `n_flags_pico_temporal == 1` E o score
desse pico é negativo (queda) E o mês é 06/2026 ou 07/2026 — os dois meses
mais recentes e incompletos na base (dados vão até jul/2026 parcial). Esses
casos tendem a ser artefato do mês estar incompleto, não uma queda real de
gasto — daí a rubrica classificar como severidade baixa.

## Regra de categoria

```
combinacao  se os 3 detectores (categoria×pares, pico temporal,
            concentração de fornecedor) sinalizaram esse deputado
senão       o sinal dominante entre os que sinalizaram
```

**Interpretação de "magnitudes relevantes"**: qualquer sinal que gerou flag
nos scripts anteriores já passou pelos limiares de `src/model.py` (score
robusto > 3,5 ou HHI > 0,25) — ou seja, já é relevante por construção. Não
foi aplicado nenhum limiar extra além dos já usados em Modeling. Por isso,
"combinação" é equivalente a `n_metodos_distintos == 3` (o script verifica
essa consistência e imprimiria um aviso se divergisse — não divergiu em
nenhum dos 50 casos).

**Desempate do "sinal dominante"** (quando só 2 dos 3 métodos sinalizaram):
cada sinal é normalizado pela distância ao próprio limiar
(`|score| / 3,5` para categoria×pares e pico temporal; `hhi / 0,25` para
concentração de fornecedor) e o maior valor normalizado vence. Em empate
exato, a ordem de prioridade fixa é categoria×pares > pico temporal >
concentração de fornecedor. Essa normalização é necessária porque score
robusto e HHI estão em escalas diferentes e não são diretamente
comparáveis — é uma aproximação razoável, não uma medida "correta" de
magnitude relativa.

## Resultado nos 50 casos

| Severidade | Casos |
|---|---:|
| Alta | 39 |
| Baixa | 8 |
| Média | 3 |

| Categoria | Casos |
|---|---:|
| Combinação | 26 |
| Gasto acima dos pares | 13 |
| Pico temporal | 8 |
| Concentração de fornecedor | 3 |

**Observação importante**: a proporção de "alta" (39/50 = 78%) é alta porque
os 50 primeiros casos de `lista_priorizada.csv` já são os de maior
confiança (ordenados por `n_metodos_distintos` desc) — 30 dos 50 já têm 5+
flags combinadas isoladamente, o que já dispara a condição de "alta" mesmo
antes de considerar valor monetário ou HHI. Isso não significa que a
rubrica esteja mal calibrada em geral; significa que ela foi aplicada sobre
uma amostra já pré-filtrada para os casos mais convergentes.

## Limitações desta rubrica

- É determinística e auditável, mas continua sendo uma regra arbitrária —
  os limiares (R$ 50.000 / R$ 10.000 / HHI 0,5 / 5 flags) não foram
  calibrados contra nenhum rótulo humano, foram escolhidos por bom senso.
- Não substitui a rotulagem humana (`severidade_humana`/`categoria_humana`
  seguem vazias neste arquivo) nem a avaliação LLM vs. humano já em
  andamento (`reports/triage_llm.csv`, `reports/rotulos_humanos.csv`).
- A regra do "fornecedor Facebook" é um caso especial adicionado
  manualmente à rubrica (provavelmente porque anúncios patrocinados são um
  gasto legítimo e comum de divulgação parlamentar) — vale revisar se faz
  sentido generalizar para outras redes sociais/plataformas de anúncio.
