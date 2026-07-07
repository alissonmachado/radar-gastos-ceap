# Evaluation — Concordância LLM vs. Referências (CEAP)

**Script:** `src/evaluate_llm.py`
**Insumos:** `reports/triage_llm.csv` (50 casos classificados pelo LLM),
`reports/rotulos_prelabel.csv` (rubrica determinística, n=50),
`reports/rotulos_humanos.csv` (rotulagem humana genuína, n=50)

Este relatório faz **duas comparações distintas e não-intercambiáveis** —
ver `reports/criterio_rotulagem.md` para por que elas não devem ser
confundidas.

## A) LLM vs. rubrica determinística (n=50)

**Isto NÃO é validação humana.** `reports/rotulos_prelabel.csv` é gerado por
`src/rubric_prelabel.py`, uma regra fixa (ver `reports/criterio_rotulagem.md`)
aplicada sobre os mesmos sinais estatísticos que alimentam o LLM. Esta
comparação mede o quanto o LLM, com um prompt genérico e sem conhecer os
limiares da rubrica, converge para a mesma classificação que uma fórmula
fixa produziria — é um teste de consistência, não de acerto.

Matriz de confusão (linhas = rubrica, colunas = LLM):

| ref \ LLM | alta | media | baixa |
|---|---:|---:|---:|
| **alta** | 5 | 28 | 6 |
| **media** | 0 | 3 | 0 |
| **baixa** | 0 | 4 | 4 |

- **Accuracy: 24.00%** (12/50)
- **Cohen's kappa: 0.104**
- **Concordância de categoria: 58.00%** (28/50)

### Hipóteses para as divergências (rubrica)

O LLM nunca recebeu os limiares da rubrica (R$ 50 mil / R$ 10 mil / HHI 0,5
/ 5+ flags / mês parcial 06-07/2026) — ele foi instruído apenas a classificar
severidade e categoria a partir do texto factual do caso (`motivo_resumo`),
com critério próprio. Por isso, divergências aqui **não são erro do LLM**:
elas mostram que o LLM pondera os sinais de forma diferente de uma fórmula
que ele nunca viu. Padrões observados nos casos divergentes:

- Quando os 3 detectores sinalizam (`n_metodos_distintos == 3`), a rubrica
  quase sempre classifica `categoria = combinacao` por definição; o LLM às
  vezes prefere nomear o sinal que parece dominante no texto, mesmo com os
  3 presentes.
- A regra de severidade "baixa" da rubrica para fornecedor Facebook ou queda
  em mês parcial é uma heurística de negócio específica (anúncio
  patrocinado é gasto comum; jul/2026 está incompleto) que o LLM não tem
  como inferir de um prompt genérico — ele não sabe que jul/2026 é parcial
  nem que "Facebook" deveria reduzir a severidade.
- **Viés de severidade**: o LLM classificou `media` em 35/50 casos (70%), independentemente do valor de referência. Isso sugere que boa parte do desacordo não é ruído aleatório, e sim uma tendência sistemática do LLM em convergir para uma única classe de severidade.
- **Viés de categoria**: o LLM classificou `combinacao` em 42/50 casos (84%). Como `combinacao` é a categoria natural quando os 3 detectores convergem, isso pode refletir o prompt levando o LLM a privilegiar essa opção sempre que o texto do caso menciona mais de um sinal, mesmo quando um dos sinais é claramente secundário.

## B) LLM vs. rotulagem humana genuína (n=50)
**50 caso(s) revisado(s) e rotulado(s) manualmente**, sem seguir a rubrica
escrita — critério do próprio revisor.

Matriz de confusão (linhas = humano, colunas = LLM):

| ref \ LLM | alta | media | baixa |
|---|---:|---:|---:|
| **alta** | 5 | 20 | 0 |
| **media** | 0 | 6 | 1 |
| **baixa** | 0 | 9 | 9 |

- **Accuracy: 40.00%** (20/50)
- **Cohen's kappa: 0.231**
- **Concordância de categoria: 28.00%** (14/50)

**Sobre o tamanho da amostra**: n=50 é modesto para accuracy/kappa — ainda
suscetível a mudar de forma notável com mais alguns casos rotulados — mas já
permite ver padrões sistemáticos (não apenas ruído de poucos pontos), ao
contrário de uma amostra n<10.

### Detalhe caso a caso

| Deputado | Severidade (ref.) | Severidade (LLM) | Concorda? | Categoria (ref.) | Categoria (LLM) | Concorda? |
|---|---|---|---|---|---|---|
| Aguinaldo Ribeiro | alta | media | ✗ | combinacao | combinacao | ✓ |
| Benedita da Silva | media | media | ✓ | combinacao | combinacao | ✓ |
| Bruno Ganem | media | media | ✓ | gasto_acima_pares | combinacao | ✗ |
| Célio Silveira | alta | alta | ✓ | pico_temporal | combinacao | ✗ |
| Elcione Barbalho | media | media | ✓ | combinacao | combinacao | ✓ |
| Ely Santos | alta | alta | ✓ | gasto_acima_pares | combinacao | ✗ |
| Erika Kokay | baixa | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Fabio Schiochet | baixa | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Gabriel Mota | alta | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Gilson Marques | baixa | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Henderson Pinto | media | media | ✓ | concentracao_fornecedor | combinacao | ✗ |
| Jeferson Rodrigues | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Josenildo | baixa | media | ✗ | combinacao | combinacao | ✓ |
| LIDERANÇA DO UNIÃO BRASIL | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Magda Mofatto | alta | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Marcos Tavares | alta | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Marx Beltrão | media | media | ✓ | concentracao_fornecedor | combinacao | ✗ |
| Mauricio do Vôlei | alta | alta | ✓ | gasto_acima_pares | combinacao | ✗ |
| Maurício Carvalho | baixa | media | ✗ | combinacao | combinacao | ✓ |
| Olival Marques | alta | alta | ✓ | combinacao | combinacao | ✓ |
| Otoni de Paula | baixa | media | ✗ | combinacao | combinacao | ✓ |
| Pastor Gil | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| Professor Alcides | alta | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Sargento Gonçalves | alta | alta | ✓ | gasto_acima_pares | combinacao | ✗ |
| Soraya Santos | alta | media | ✗ | combinacao | combinacao | ✓ |
| Sâmia Bomfim | baixa | media | ✗ | combinacao | combinacao | ✓ |
| Adilson Barroso | baixa | baixa | ✓ | combinacao | pico_temporal | ✗ |
| Afonso Hamm | baixa | baixa | ✓ | combinacao | combinacao | ✓ |
| Afonso Motta | baixa | baixa | ✓ | combinacao | combinacao | ✓ |
| Albuquerque | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| Alceu Moreira | baixa | baixa | ✓ | combinacao | combinacao | ✓ |
| Alex Manente | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Alexandre Lindenmeyer | baixa | baixa | ✓ | combinacao | pico_temporal | ✗ |
| Alfredo Gaspar | baixa | baixa | ✓ | combinacao | concentracao_fornecedor | ✗ |
| Aluisio Mendes | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Amanda Gentil | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Ana Paula Lima | baixa | baixa | ✓ | combinacao | pico_temporal | ✗ |
| Andreia Siqueira | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| André Fernandes | baixa | media | ✗ | combinacao | combinacao | ✓ |
| André Janones | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| Antonio Carlos Rodrigues | baixa | media | ✗ | combinacao | combinacao | ✓ |
| Antônio Doido | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Arlindo Chinaglia | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| Arnaldo Jardim | alta | media | ✗ | concentracao_fornecedor | combinacao | ✗ |
| Arthur Lira | alta | media | ✗ | pico_temporal | combinacao | ✗ |
| Aureo Ribeiro | alta | media | ✗ | gasto_acima_pares | combinacao | ✗ |
| Bandeira de Mello | media | baixa | ✗ | combinacao | pico_temporal | ✗ |
| Bibo Nunes | baixa | baixa | ✓ | combinacao | pico_temporal | ✗ |
| Bohn Gass | baixa | baixa | ✓ | combinacao | gasto_acima_pares | ✗ |
| Bruno Farias | media | media | ✓ | combinacao | pico_temporal | ✗ |

### Hipóteses para as divergências (humano)

- Quando os 3 detectores estatísticos sinalizam o mesmo deputado, o LLM
  tende a rotular `categoria_anomalia` como `combinacao` quase
  mecanicamente. Um revisor humano, ao olhar o `motivo_resumo` completo,
  pode julgar que um dos três sinais é claramente mais relevante (ex.: um
  valor pequeno numa categoria, ou um fornecedor concentrado que é uma
  plataforma de publicidade comum) e preferir rotular pelo sinal dominante
  em vez de "combinação". Consistente com a limitação já registrada em
  `reports/evaluation.md`: os 3 métodos não são totalmente independentes.
- Divergências de severidade podem surgir quando o LLM pondera a
  convergência dos métodos (`combinacao` → severidade mais alta por
  default) enquanto o humano pondera mais a plausibilidade do fornecedor
  concentrado ou o tamanho absoluto do valor.
- **Viés de severidade**: o LLM classificou `media` em 35/50 casos (70%), independentemente do valor de referência. Isso sugere que boa parte do desacordo não é ruído aleatório, e sim uma tendência sistemática do LLM em convergir para uma única classe de severidade.
- **Viés de categoria**: o LLM classificou `combinacao` em 42/50 casos (84%). Como `combinacao` é a categoria natural quando os 3 detectores convergem, isso pode refletir o prompt levando o LLM a privilegiar essa opção sempre que o texto do caso menciona mais de um sinal, mesmo quando um dos sinais é claramente secundário.

## Limitações gerais desta avaliação

- A comparação com a rubrica (A) mede consistência com uma regra fixa, não
  qualidade de julgamento — um kappa alto ali não implica que o LLM "acerta
  mais", só que converge com uma fórmula específica.
- A comparação com humano (B) já tem n suficiente para ver padrões
  sistemáticos, mas ainda é uma amostra única (um só revisor, sem segundo
  avaliador para medir concordância entre humanos) — não deve ser tratada
  como validação definitiva da qualidade do LLM.
- Nenhuma das duas comparações substitui a outra. Tratar (A) como se fosse
  "validação humana" seria uma caracterização falsa da metodologia — a
  distinção é mantida deliberadamente neste relatório.
