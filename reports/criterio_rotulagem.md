# Critério de Rotulagem — Rubrica Automática e Rotulagem Humana (CEAP)

**Script da rubrica automática:** `src/rubric_prelabel.py`
**Insumos:** `reports/lista_priorizada.csv` (50 primeiros casos),
`data/processed/outliers_categoria_pares.csv`,
`data/processed/picos_temporais.csv`,
`data/processed/concentracao_fornecedor.csv`
**Saída da rubrica automática:** `reports/rotulos_prelabel.csv`
**Saída da rotulagem humana:** `reports/rotulos_humanos.csv`

## Por que existe

Antes de comparar o LLM (`reports/triage_llm.csv`) contra rotulagem humana,
é útil ter um terceiro ponto de referência **determinístico** (sem
subjetividade, sem custo de API): uma rubrica fixa aplicada sobre os mesmos
sinais estatísticos já calculados em Modeling/Evaluation. Isso não substitui
o rótulo humano — é um rascunho auditável para acelerar a revisão.

**Dois arquivos, dois propósitos diferentes:**

- `reports/rotulos_prelabel.csv` (`src/rubric_prelabel.py`): rubrica
  **100% automática**, sem intervenção humana. Usa o sinal correto
  (`max(categoria, pico)`) desde o início. Serve como referência de
  consistência — não é rotulagem humana.
- `reports/rotulos_humanos.csv`: rotulagem **humana real, feita em duas
  etapas** (detalhado abaixo), n=50. É a referência principal de
  `src/evaluate_llm.py` para medir concordância do LLM com julgamento
  humano.

## Metodologia da rotulagem humana (duas etapas)

**Etapa 1 — rotulagem inicial pelo sinal categoria×pares.** O autor revisou
os 50 casos usando uma planilha de apoio que exibia apenas o valor do
detector de categoria×pares (o primeiro sinal mencionado no
`motivo_resumo` de cada caso) — não o valor do detector de pico temporal,
mesmo quando este também estava presente no texto completo. Na prática, o
critério aplicado nesta etapa foi "sinal = valor da categoria×pares", não
"sinal principal = maior valor entre categoria e pico" (a definição
original da rubrica).

**Etapa 2 — segunda passada nos casos em que o pico muda a classe.**
Comparando "severidade com sinal = só categoria" vs. "severidade com sinal
= max(categoria, pico)" (a definição correta), apenas **2 dos 50 casos
(4%)** teriam classe de severidade diferente:

| Deputado | Sinal categoria (só) | Sinal max (c/ pico) | Severidade etapa 1 | Severidade final (etapa 2) |
|---|---:|---:|---|---|
| Aguinaldo Ribeiro | R$ 24.700,40 | R$ 69.833,94 | media | **alta** |
| Bruno Ganem | R$ 1.350,00 | R$ 53.397,60 | baixa | **alta** |

O autor revisou manualmente esses 2 casos à luz do sinal completo:

- **Aguinaldo Ribeiro → alta**: os três detectores convergem no mesmo mês
  (06/2025) e o maior valor entre os sinais (R$ 69.833,94) ultrapassa o
  limiar de R$ 50 mil.
- **Bruno Ganem → alta**: o sinal de pico corrigido (R$ 53.397,60) já
  ultrapassa sozinho o limiar de R$ 50 mil, o que satisfaz a condição
  "alta" da rubrica independentemente da concentração em fornecedor
  (Facebook, 55% do gasto identificado). Mantivemos a precedência já
  documentada abaixo — "alta" é verificada antes de "baixa" — para não
  criar uma exceção ad hoc que não se aplica aos outros 48 casos: se o
  sinal monetário já qualifica como "alta", o motivo de "baixa" ligado ao
  fornecedor Facebook não é avaliado.

Os outros 48 casos mantêm a classificação da etapa 1 sem alteração — nesses
casos, o valor do pico não teria mudado a classe de severidade (seja porque
o pico não é maior que o valor da categoria, seja porque a classe já era
"alta" por outro critério independente do valor monetário, como HHI ≥ 0,5
ou 5+ flags combinadas).

**Limitação reconhecida**: a etapa 1 não seguiu a definição literal de
"sinal principal" da rubrica (usou só categoria, não o máximo). A etapa 2
corrige isso apenas nos casos em que a diferença muda o resultado — não foi
feita uma re-revisão completa dos 50 casos sob a definição correta, então é
possível (embora, pela análise acima, matematicamente descartado para
severidade) que a categoria (`categoria_humana`) de algum caso também
tivesse sido diferente se o revisor tivesse visto o valor do pico desde o
início.

## Regra da rubrica automática (`src/rubric_prelabel.py` → `rotulos_prelabel.csv`)

As duas seções abaixo descrevem a rubrica **100% automática**, usada como
referência de consistência (não como rotulagem humana) e também como base
que orientou — mas não foi seguida à risca na etapa 1 — a rotulagem humana
descrita acima.

### Regra de severidade

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

### Regra de categoria

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

### Resultado da rubrica automática nos 50 casos (`rotulos_prelabel.csv`)

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
uma amostra já pré-filtrada para os casos mais convergentes. (A rotulagem
humana, por ter usado só o sinal de categoria na etapa 1, não reproduz
exatamente essa distribuição — ver contagem em `reports/rotulos_humanos.csv`.)

### Limitações da rubrica automática

- É determinística e auditável, mas continua sendo uma regra arbitrária —
  os limiares (R$ 50.000 / R$ 10.000 / HHI 0,5 / 5 flags) não foram
  calibrados contra nenhum rótulo humano, foram escolhidos por bom senso.
- `reports/rotulos_prelabel.csv` não é rotulagem humana: suas colunas
  `severidade_humana`/`categoria_humana` ficam vazias de propósito. A
  rotulagem humana real está em `reports/rotulos_humanos.csv` (ver
  metodologia em duas etapas, acima).
- A regra do "fornecedor Facebook" é um caso especial adicionado
  manualmente à rubrica (provavelmente porque anúncios patrocinados são um
  gasto legítimo e comum de divulgação parlamentar) — o caso Bruno Ganem
  (acima) mostra que essa regra só atua quando nenhuma condição de "alta"
  já foi satisfeita; vale revisar se essa precedência é a desejada, e se
  faz sentido generalizar a regra para outras redes sociais/plataformas de
  anúncio.
