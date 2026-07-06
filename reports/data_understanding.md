# Data Understanding — Cota para o Exercício da Atividade Parlamentar (CEAP)

**Fonte dos dados:** [camara.leg.br/cotas](https://www.camara.leg.br/cotas/) — arquivos `Ano-2025.csv.zip` e `Ano-2026.csv.zip`.
**Script de geração:** `src/explore.py`
**Dados processados:** `data/processed/gasto_mensal_por_deputado.csv`

## 1. Volume e estrutura dos dados

| Item | Valor |
|---|---|
| Linhas totais (2025 + 2026) | 284.845 |
| Colunas | 33 |
| Período coberto | 2025 (ano completo) e 2026 (parcial, até jul/2026) |

### Nulos por coluna (destaques)

| Coluna | % nulos | Observação |
|---|---:|---|
| `datPagamentoRestituicao` | 99,98% | quase nunca há restituição |
| `vlrRestituicao` | 99,98% | idem |
| `txtTrecho` | 86,74% | só preenchido em passagens aéreas |
| `txtPassageiro` | 86,70% | idem |
| `txtDescricaoEspecificacao` | 62,30% | subcategoria opcional |
| `urlDocumento` | 18,93% | nem todo documento tem PDF público |
| `txtCNPJCPF` | 13,03% | ver seção de qualidade |
| `cpf`, `ideCadastro`, `nuCarteiraParlamentar`, `sgUF`, `sgPartido` | 0,48% | registros de lideranças partidárias (`LID.GOV-CD` etc.) sem vínculo individual |
| Demais colunas (`vlrLiquido`, `numMes`, `numAno`, `txtDescricao`, `txtFornecedor`, ...) | 0,00% | completas |

Tipos: majoritariamente `str` (texto) e `float64`/`int64` para valores e identificadores. Datas (`datEmissao`) estão como texto no formato ISO, não convertidas para `datetime` nesta etapa.

## 2. Total gasto por ano (`vlrLiquido`)

| Ano | Total gasto |
|---|---:|
| 2025 | R$ 242.224.027,84 |
| 2026 (parcial) | R$ 102.865.973,95 |

## 3. Top 10 por gasto total

**Deputados**

| # | Deputado | Total |
|---|---|---:|
| 1 | Albuquerque | R$ 963.796,66 |
| 2 | Carlos Veras | R$ 916.184,27 |
| 3 | Ruy Carneiro | R$ 901.478,95 |
| 4 | Gabriel Mota | R$ 898.578,60 |
| 5 | Geraldo Resende | R$ 897.855,54 |
| 6 | Pompeo de Mattos | R$ 896.384,43 |
| 7 | João Maia | R$ 893.708,34 |
| 8 | Flávio Nogueira | R$ 893.520,19 |
| 9 | Zé Adriano | R$ 891.882,95 |
| 10 | Rodolfo Nogueira | R$ 887.768,05 |

**Categorias de despesa (`txtDescricao`)**

| # | Categoria | Total |
|---|---|---:|
| 1 | Divulgação da atividade parlamentar | R$ 151.258.844,30 |
| 2 | Locação ou fretamento de veículos automotores | R$ 61.439.674,96 |
| 3 | Manutenção de escritório de apoio à atividade parlamentar | R$ 48.617.031,40 |
| 4 | Combustíveis e lubrificantes | R$ 33.946.418,07 |
| 5 | Passagem aérea - SIGEPA | R$ 27.115.521,73 |
| 6 | Hospedagem (exceto do parlamentar no DF) | R$ 6.145.082,43 |
| 7 | Telefonia | R$ 3.887.053,39 |
| 8 | Locação ou fretamento de aeronaves | R$ 3.718.653,00 |
| 9 | Fornecimento de alimentação do parlamentar | R$ 2.072.183,32 |
| 10 | Serviço de segurança prestado por empresa especializada | R$ 1.891.528,69 |

Divulgação da atividade parlamentar concentra sozinha ~54% do total gasto nas top 10 categorias — maior ponto de atenção para a próxima fase.

**Fornecedores (`txtFornecedor`)**

| # | Fornecedor | Total |
|---|---|---:|
| 1 | TAM | R$ 16.373.861,63 |
| 2 | GOL | R$ 6.052.293,88 |
| 3 | AZUL | R$ 4.696.441,72 |
| 4 | Pantanal Veículos LTDA | R$ 4.632.893,41 |
| 5 | Facebook Serviços Online do Brasil Ltda. | R$ 4.238.425,58 |
| 6 | Suprema Mobilidade LTDA | R$ 1.993.569,37 |
| 7 | HPE Automotores do Brasil LTDA | R$ 1.955.710,01 |
| 8 | Novacar Locadora de Veiculos LTDA | R$ 1.638.443,13 |
| 9 | Eldorado Comunicação e Jornalismo LTDA | R$ 1.277.328,57 |
| 10 | Via Locadora de Automoveis LTDA | R$ 1.245.059,45 |

Companhias aéreas dominam o topo; Facebook aparece como fornecedor relevante, coerente com a categoria "divulgação da atividade parlamentar".

## 4. Achados de qualidade dos dados

| Verificação | Quantidade |
|---|---:|
| Registros com `vlrLiquido` negativo | 7.191 |
| Registros com CNPJ na faixa inválida `00.000.000/0000-01` a `07` | 8.527 |

Detalhe dos códigos inválidos encontrados:

| Código | Ocorrências |
|---|---:|
| `00000000000001` | 3.995 |
| `00000000000002` | 14 |
| `00000000000006` | 4.518 |

Não foram encontrados registros com os códigos `...03`, `...04`, `...05` ou `...07`. Esses CNPJs "genéricos" provavelmente indicam despesas sem fornecedor identificável formalmente (ex.: ressarcimentos, casos sem nota fiscal eletrônica) e devem ser tratados/sinalizados na fase de Data Preparation.

Valores negativos em `vlrLiquido` provavelmente correspondem a estornos/glosas e também merecem regra de tratamento explícita antes da modelagem.

## 5. Distribuição do gasto mensal por deputado

Calculado sobre 601 combinações deputado × mês com despesa registrada.

| Estatística | Média | Mediana | Desvio padrão | Máximo |
|---|---:|---:|---:|---:|
| Média geral entre deputados | R$ 34.859,72 | R$ 34.447,64 | R$ 14.632,47 | R$ 62.139,82 |
| Mínimo observado | R$ 0,03 | R$ 0,03 | R$ 0,21 | R$ 0,03 |
| Máximo observado | R$ 56.693,92 | R$ 54.984,97 | R$ 44.613,00 | R$ 207.497,05 |

**Top 10 deputados por média de gasto mensal:**

| # | Deputado | Média | Mediana | Desvio | Máximo |
|---|---|---:|---:|---:|---:|
| 1 | Albuquerque | R$ 56.693,92 | R$ 48.148,70 | R$ 15.438,00 | R$ 82.655,81 |
| 2 | Gabriel Mota | R$ 52.857,56 | R$ 51.612,68 | R$ 4.765,54 | R$ 58.000,00 |
| 3 | Silas Câmara | R$ 51.942,18 | R$ 48.733,54 | R$ 43.504,70 | R$ 144.692,13 |
| 4 | Wilson Santiago | R$ 51.221,02 | R$ 54.984,97 | R$ 12.509,58 | R$ 77.619,91 |
| 5 | Ruy Carneiro | R$ 50.082,16 | R$ 50.038,33 | R$ 16.011,29 | R$ 86.721,33 |
| 6 | Geraldo Resende | R$ 49.880,86 | R$ 49.120,01 | R$ 23.085,84 | R$ 88.730,13 |
| 7 | Pompeo de Mattos | R$ 49.799,14 | R$ 51.190,96 | R$ 16.507,54 | R$ 97.510,07 |
| 8 | Flávio Nogueira | R$ 49.640,01 | R$ 47.318,02 | R$ 9.433,13 | R$ 80.613,37 |
| 9 | Zé Adriano | R$ 49.549,05 | R$ 48.279,07 | R$ 27.551,98 | R$ 106.811,63 |
| 10 | Coronel Ulysses | R$ 48.951,74 | R$ 49.181,33 | R$ 13.109,49 | R$ 84.089,72 |

Deputados como Silas Câmara e Zé Adriano têm desvio padrão elevado em relação à média — indício de gasto concentrado em poucos meses (picos), o que pode ser investigado na fase de Data Preparation/EDA.

Tabela completa (601 deputados) disponível em `data/processed/gasto_mensal_por_deputado.csv`.

## 6. Próximos passos sugeridos

1. Definir regra de tratamento para `vlrLiquido` negativo (excluir, manter como estorno, ou compensar contra o lançamento original).
2. Definir regra para CNPJs genéricos (`...01/02/06`): manter como categoria própria "sem fornecedor identificado" em vez de excluir.
3. Converter `datEmissao` para `datetime` e padronizar `txtCNPJCPF` (remover formatação) na fase de Data Preparation.
4. Investigar concentração de gasto em "Divulgação da atividade parlamentar" por partido/UF — pode indicar padrões de uso da cota que vale segmentar.
