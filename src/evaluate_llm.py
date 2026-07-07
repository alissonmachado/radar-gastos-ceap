"""Evaluation: concordância entre triagem por LLM e rotulagem humana (CEAP)."""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

SEVERIDADES = ["alta", "media", "baixa"]


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def cohen_kappa(confusao: pd.DataFrame) -> float:
    """Cohen's kappa a partir de uma matriz de confusão (linhas=humano, colunas=LLM)."""
    n = confusao.values.sum()
    po = confusao.values.trace() / n
    marg_humano = confusao.sum(axis=1) / n
    marg_llm = confusao.sum(axis=0) / n
    pe = sum(marg_humano[c] * marg_llm[c] for c in confusao.index)
    if pe == 1:
        return float("nan")
    return (po - pe) / (1 - pe)


def carregar_merge() -> pd.DataFrame:
    llm = pd.read_csv(REPORTS_DIR / "triage_llm.csv", encoding="utf-8")
    humano = pd.read_csv(REPORTS_DIR / "rotulos_humanos.csv", encoding="utf-8-sig")

    merged = humano.merge(llm, on="txNomeParlamentar", how="inner")

    nao_encontrados_no_llm = set(humano["txNomeParlamentar"]) - set(llm["txNomeParlamentar"])
    nao_rotulados = set(llm["txNomeParlamentar"]) - set(humano["txNomeParlamentar"])

    print(f"Rótulos humanos: {len(humano)} | Casos no triage LLM: {len(llm)} | Correspondências: {len(merged)}")
    if nao_encontrados_no_llm:
        print(f"AVISO: {len(nao_encontrados_no_llm)} rótulo(s) humano(s) sem correspondência no triage LLM: {sorted(nao_encontrados_no_llm)}")
    if nao_rotulados:
        print(f"Casos do triage LLM ainda sem rótulo humano: {len(nao_rotulados)}")

    return merged


def avaliar_severidade(merged: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    section("Severidade: LLM vs. humano")

    confusao = pd.crosstab(merged["severidade_humana"], merged["severidade"])
    confusao = confusao.reindex(index=SEVERIDADES, columns=SEVERIDADES, fill_value=0)

    accuracy = (merged["severidade_humana"] == merged["severidade"]).mean()
    kappa = cohen_kappa(confusao)

    print("Matriz de confusão (linhas=humano, colunas=LLM):")
    print(confusao.to_string())
    print(f"\nAccuracy: {accuracy:.2%}")
    print(f"Cohen's kappa: {kappa:.3f}")

    return confusao, accuracy, kappa


def avaliar_categoria(merged: pd.DataFrame) -> float:
    section("Categoria: LLM vs. humano")

    concordancia = (merged["categoria_humana"] == merged["categoria_anomalia"]).mean()
    print(f"% de concordância na categoria: {concordancia:.2%}")

    print("\nDetalhe:")
    print(
        merged[["txNomeParlamentar", "categoria_humana", "categoria_anomalia"]]
        .assign(concorda=lambda d: d["categoria_humana"] == d["categoria_anomalia"])
        .to_string(index=False)
    )

    return concordancia


def gerar_relatorio(merged: pd.DataFrame, confusao: pd.DataFrame, accuracy: float, kappa: float, concordancia_categoria: float) -> None:
    n = len(merged)

    disagreements_sev = merged[merged["severidade_humana"] != merged["severidade"]]
    disagreements_cat = merged[merged["categoria_humana"] != merged["categoria_anomalia"]]

    linhas_confusao = "\n".join(
        f"| **{idx}** | {row['alta']} | {row['media']} | {row['baixa']} |"
        for idx, row in confusao.iterrows()
    )

    linhas_detalhe = "\n".join(
        f"| {r['txNomeParlamentar']} | {r['severidade_humana']} | {r['severidade']} | "
        f"{'✓' if r['severidade_humana'] == r['severidade'] else '✗'} | "
        f"{r['categoria_humana']} | {r['categoria_anomalia']} | "
        f"{'✓' if r['categoria_humana'] == r['categoria_anomalia'] else '✗'} |"
        for _, r in merged.iterrows()
    )

    conteudo = f"""# Evaluation — Concordância LLM vs. Rotulagem Humana (CEAP)

**Script:** `src/evaluate_llm.py`
**Insumos:** `reports/triage_llm.csv` (30 casos classificados pelo LLM),
`reports/rotulos_humanos.csv` (rotulagem manual independente)

## Aviso sobre o tamanho da amostra

**N = {n} casos com rótulo humano até o momento**, de um total de 30
classificados pelo LLM. Com uma amostra dessa dimensão, accuracy e Cohen's
kappa têm intervalo de confiança enorme — um único caso a mais ou a menos
muda o resultado de forma substancial. Os números abaixo são um retrato
preliminar, não uma validação estatística robusta do LLM. A rotulagem
humana das demais linhas de `reports/triage_llm.csv` deve continuar para
que essa avaliação ganhe poder estatístico.

## Severidade: LLM vs. humano

Matriz de confusão (linhas = rótulo humano, colunas = rótulo do LLM):

| humano \\ LLM | alta | media | baixa |
|---|---:|---:|---:|
{linhas_confusao}

- **Accuracy: {accuracy:.2%}** ({int(accuracy * n)}/{n} casos com severidade idêntica)
- **Cohen's kappa: {kappa:.3f}**

Cohen's kappa corrige a concordância bruta pelo acordo esperado ao acaso
dado o desbalanceamento das classes. Com N={n}, mesmo um kappa
"substancial" (na escala usual de Landis & Koch, > 0,6) não deve ser lido
como "o LLM está calibrado" — é consistente tanto com um classificador bom
quanto com sorte em uma amostra pequena.

## Categoria: % de concordância

**{concordancia_categoria:.0%} de concordância** ({int(concordancia_categoria * n)}/{n} casos com
`categoria_anomalia` idêntica a `categoria_humana`).

## Detalhe caso a caso

| Deputado | Severidade (humano) | Severidade (LLM) | Concorda? | Categoria (humano) | Categoria (LLM) | Concorda? |
|---|---|---|---|---|---|---|
{linhas_detalhe}

## Análise honesta das divergências

"""

    if disagreements_sev.empty and disagreements_cat.empty:
        conteudo += "Nenhuma divergência nos casos rotulados até agora — mas com N tão pequeno, isso é fraca evidência de que o LLM está bem calibrado; é preciso rotular mais casos antes de tirar conclusões.\n"
    else:
        conteudo += (
            "Casos com divergência (ver também `reports/lista_priorizada.csv` para o "
            "`motivo_resumo` completo de cada um):\n\n"
        )
        for _, r in pd.concat([disagreements_sev, disagreements_cat]).drop_duplicates(subset="txNomeParlamentar").iterrows():
            conteudo += f"- **{r['txNomeParlamentar']}**: humano = `{r['severidade_humana']}`/`{r['categoria_humana']}`, LLM = `{r['severidade']}`/`{r['categoria_anomalia']}`.\n"

        conteudo += """
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
"""

    conteudo += """
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
"""

    destino = REPORTS_DIR / "evaluation_llm.md"
    destino.write_text(conteudo, encoding="utf-8")
    print(f"\nSalvo: {destino}")


def main() -> None:
    merged = carregar_merge()
    confusao, accuracy, kappa = avaliar_severidade(merged)
    concordancia_categoria = avaliar_categoria(merged)
    gerar_relatorio(merged, confusao, accuracy, kappa, concordancia_categoria)


if __name__ == "__main__":
    main()
