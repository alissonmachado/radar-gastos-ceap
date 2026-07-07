# Radar de Gastos da Cota Parlamentar (CEAP)

Projeto individual (CRISP-DM) de análise dos gastos da Cota para o Exercício
da Atividade Parlamentar (CEAP) da Câmara dos Deputados, com o objetivo de
**priorizar** — não acusar — padrões de gasto que fogem do usual e merecem
atenção de cidadãos, jornalistas e auditores.

## Estrutura

```
data/raw/          downloads originais (Ano-2025.csv, Ano-2026.csv) — gerado localmente, fora do git
data/processed/     dados intermediários de cada fase — gerado localmente, fora do git
src/                pipeline, uma etapa por script (ver abaixo)
notebooks/          exploração pontual
reports/            relatórios e a lista priorizada final (versionados no git)
```

## Pipeline

Cada fase do CRISP-DM corresponde a um script em `src/`, executado nesta ordem:

```bash
pip install pandas pyarrow

python src/explore.py    # Data Understanding — perfil dos dados brutos
python src/prepare.py    # Data Preparation  — limpeza, tipagem, flags, agregações
python src/model.py      # Modeling          — 3 detectores estatísticos de outliers
python src/evaluate.py   # Evaluation        — sensibilidade, triangulação, amostra p/ revisão
python src/deploy.py     # Deployment        — lista priorizada final
```

Antes de rodar, baixe e descompacte os arquivos de origem em `data/raw/`:
- https://www.camara.leg.br/cotas/Ano-2025.csv.zip
- https://www.camara.leg.br/cotas/Ano-2026.csv.zip

## Relatórios

- `reports/data_understanding.md` — perfil inicial dos dados brutos.
- `reports/relatorio_final.md` — relatório final em linguagem cidadã, com a
  lista priorizada e as limitações do método.
- `reports/lista_priorizada.csv` — saída de `src/deploy.py`: deputados
  sinalizados por 2 ou mais dos 3 detectores, com o motivo resumido.

## Metodologia (resumo)

Três detectores estatísticos independentes (mediana + MAD, "score robusto",
menos sensível a valores extremos que média/desvio padrão comuns):

1. **Categoria × pares**: gasto mensal de um deputado numa categoria vs.
   outros deputados na mesma categoria/mês.
2. **Concentração de fornecedor (HHI)**: quanto do gasto de um deputado está
   concentrado num único fornecedor.
3. **Pico temporal**: meses que fogem do padrão histórico do próprio deputado.

Um deputado sinalizado por 2 ou mais métodos distintos entra na lista
priorizada — ver `reports/relatorio_final.md` para achados, ressalvas e
limitações.
