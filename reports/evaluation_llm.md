# Evaluation — Concordância LLM vs. Rotulagem Humana (CEAP)

**Script:** `src/evaluate_llm.py`
**Insumos:** `reports/triage_llm.csv` (30 casos classificados pelo LLM),
`reports/rotulos_humanos.csv` (rotulagem manual independente)

## Aviso sobre o tamanho da amostra

**N = 4 casos com rótulo humano até o momento**, de um total de 30
classificados pelo LLM. Com uma amostra dessa dimensão, accuracy e Cohen's
kappa têm intervalo de confiança enorme — um único caso a mais ou a menos
muda o resultado de forma substancial. Os números abaixo são um retrato
preliminar, não uma validação estatística robusta do LLM. A rotulagem
humana das demais linhas de `reports/triage_llm.csv` deve continuar para
que essa avaliação ganhe poder estatístico.

## Severidade: LLM vs. humano

Matriz de confusão (linhas = rótulo humano, colunas = rótulo do LLM):

| humano \ LLM | alta | media | baixa |
|---|---:|---:|---:|
| **alta** | 2 | 0 | 0 |
| **media** | 0 | 1 | 0 |
| **baixa** | 0 | 1 | 0 |

- **Accuracy: 75.00%** (3/4 casos com severidade idêntica)
- **Cohen's kappa: 0.600**

Cohen's kappa corrige a concordância bruta pelo acordo esperado ao acaso
dado o desbalanceamento das classes. Com N=4, mesmo um kappa
"substancial" (na escala usual de Landis & Koch, > 0,6) não deve ser lido
como "o LLM está calibrado" — é consistente tanto com um classificador bom
quanto com sorte em uma amostra pequena.

## Categoria: % de concordância

**50% de concordância** (2/4 casos com
`categoria_anomalia` idêntica a `categoria_humana`).

## Detalhe caso a caso

| Deputado | Severidade (humano) | Severidade (LLM) | Concorda? | Categoria (humano) | Categoria (LLM) | Concorda? |
|---|---|---|---|---|---|---|
| Aguinaldo Ribeiro | media | media | ✓ | combinacao | combinacao | ✓ |
| Bruno Ganem | baixa | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Célio Silveira | alta | alta | ✓ | combinacao | combinacao | ✓ |
| Sargento Gonçalves | alta | alta | ✓ | gasto_acima_pares | combinacao | ✗ |

## Análise honesta das divergências

Casos com divergência (ver também `reports/lista_priorizada.csv` para o `motivo_resumo` completo de cada um):

- **Bruno Ganem**: humano = `baixa`/`concentracao_fornecedor`, LLM = `media`/`combinacao`.
- **Sargento Gonçalves**: humano = `alta`/`gasto_acima_pares`, LLM = `alta`/`combinacao`.

Hipóteses para as divergências observadas (não são certezas — são leituras
qualitativas dos casos, a confirmar com mais rótulos):

- Quando os 3 detectores estatísticos sinalizam o mesmo deputado
  (`n_metodos_distintos == 3`), o LLM tende a rotular `categoria_anomalia`
  como `combinacao` quase mecanicamente. Um revisor humano, ao olhar o
  `motivo_resumo` completo, pode julgar que um dos três sinais é
  claramente mais relevante que os outros dois (ex.: um valor monetário
  muito pequeno numa categoria, ou um fornecedor concentrado que é uma
  plataforma de publicidade comum como Facebook) e preferir rotular pelo
  sinal dominante em vez de "combinação". Isso é consistente com a
  limitação já registrada em `reports/evaluation.md`: os 3 métodos não são
  totalmente independentes — picos temporais e outliers de categoria
  frequentemente capturam o mesmo evento de gasto (ex.: um mês pesado em
  "Divulgação da Atividade Parlamentar" aciona os dois detectores ao mesmo
  tempo), então "3 métodos concordam" nem sempre significa 3 evidências
  independentes.
- Divergências de severidade podem surgir quando o LLM pondera a
  convergência dos métodos (`combinacao` → severidade mais alta por
  default) enquanto o humano pondera mais a plausibilidade do fornecedor
  concentrado ou o tamanho absoluto do valor. Isso é o mesmo padrão que a
  rubrica determinística de `src/rubric_prelabel.py` tenta capturar
  explicitamente com a regra "fornecedor Facebook → severidade baixa" — se
  o humano aplicou raciocínio parecido, a divergência é esperada e não
  indica erro do LLM, só um critério diferente de peso entre sinais.

## Limitações desta avaliação

- Amostra pequena (ver aviso acima) — não há poder estatístico para
  afirmar que o LLM concorda ou diverge do humano de forma geral.
- A rotulagem humana usada aqui não seguiu uma rubrica escrita (diferente
  de `src/rubric_prelabel.py`), então parte da divergência entre humano e
  LLM pode refletir apenas critérios implícitos e não documentados do
  revisor, não necessariamente um erro do LLM.
- Esta avaliação não substitui a comparação com a pré-rotulagem por
  rubrica (`reports/rotulos_prelabel.csv`) nem a análise de sensibilidade
  já feita em `reports/evaluation.md` — são três ângulos complementares,
  nenhum suficiente sozinho.
