"""Evaluation: concordância entre triagem por LLM e duas referências (CEAP).

Duas comparações distintas e não-intercambiáveis:
  A) LLM vs. rubrica determinística (n=50, reports/rotulos_prelabel.csv) —
     mede se o LLM reproduz uma regra fixa e conhecida. NÃO é validação humana.
  B) LLM vs. rotulagem humana genuína (n atual, reports/rotulos_humanos.csv) —
     rótulos digitados por quem revisou os casos, sem seguir uma rubrica escrita.
"""

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
    """Cohen's kappa a partir de uma matriz de confusão (linhas=referência, colunas=LLM)."""
    n = confusao.values.sum()
    po = confusao.values.trace() / n
    marg_ref = confusao.sum(axis=1) / n
    marg_llm = confusao.sum(axis=0) / n
    pe = sum(marg_ref[c] * marg_llm[c] for c in confusao.index)
    if pe == 1:
        return float("nan")
    return (po - pe) / (1 - pe)


def avaliar(merged: pd.DataFrame, sev_ref_col: str, cat_ref_col: str, label: str) -> dict:
    section(f"{label}: LLM vs. {sev_ref_col}/{cat_ref_col} (n={len(merged)})")

    confusao = pd.crosstab(merged[sev_ref_col], merged["severidade"])
    confusao = confusao.reindex(index=SEVERIDADES, columns=SEVERIDADES, fill_value=0)

    accuracy = (merged[sev_ref_col] == merged["severidade"]).mean()
    kappa = cohen_kappa(confusao)
    concordancia_categoria = (merged[cat_ref_col] == merged["categoria_anomalia"]).mean()

    print("Matriz de confusão (linhas=referência, colunas=LLM):")
    print(confusao.to_string())
    print(f"Accuracy: {accuracy:.2%} | Cohen's kappa: {kappa:.3f} | Concordância categoria: {concordancia_categoria:.2%}")

    disagreements = merged[(merged[sev_ref_col] != merged["severidade"]) | (merged[cat_ref_col] != merged["categoria_anomalia"])]

    moda_severidade_llm = merged["severidade"].value_counts()
    moda_categoria_llm = merged["categoria_anomalia"].value_counts()

    return {
        "n": len(merged),
        "confusao": confusao,
        "accuracy": accuracy,
        "kappa": kappa,
        "concordancia_categoria": concordancia_categoria,
        "merged": merged,
        "sev_ref_col": sev_ref_col,
        "cat_ref_col": cat_ref_col,
        "disagreements": disagreements,
        "moda_severidade_llm": moda_severidade_llm,
        "moda_categoria_llm": moda_categoria_llm,
    }


def carregar_merge(llm: pd.DataFrame, referencia: pd.DataFrame) -> pd.DataFrame:
    merged = referencia.merge(llm, on="txNomeParlamentar", how="inner")
    faltantes = set(referencia["txNomeParlamentar"]) - set(llm["txNomeParlamentar"])
    if faltantes:
        print(f"AVISO: {len(faltantes)} nome(s) na referência sem correspondência no triage LLM: {sorted(faltantes)}")
    return merged


def tabela_confusao_md(confusao: pd.DataFrame) -> str:
    linhas = "\n".join(
        f"| **{idx}** | {row['alta']} | {row['media']} | {row['baixa']} |" for idx, row in confusao.iterrows()
    )
    return f"| ref \\ LLM | alta | media | baixa |\n|---|---:|---:|---:|\n{linhas}"


def tabela_detalhe_md(merged: pd.DataFrame, sev_ref_col: str, cat_ref_col: str) -> str:
    linhas = []
    for _, r in merged.iterrows():
        sev_ok = "✓" if r[sev_ref_col] == r["severidade"] else "✗"
        cat_ok = "✓" if r[cat_ref_col] == r["categoria_anomalia"] else "✗"
        linhas.append(
            f"| {r['txNomeParlamentar']} | {r[sev_ref_col]} | {r['severidade']} | {sev_ok} | "
            f"{r[cat_ref_col]} | {r['categoria_anomalia']} | {cat_ok} |"
        )
    return "| Deputado | Severidade (ref.) | Severidade (LLM) | Concorda? | Categoria (ref.) | Categoria (LLM) | Concorda? |\n|---|---|---|---|---|---|---|\n" + "\n".join(linhas)


def analisar_vies_llm(resultado: dict) -> str:
    n = resultado["n"]
    moda_sev = resultado["moda_severidade_llm"]
    moda_cat = resultado["moda_categoria_llm"]
    sev_dominante = moda_sev.idxmax()
    cat_dominante = moda_cat.idxmax()
    pct_sev = moda_sev.max() / n
    pct_cat = moda_cat.max() / n

    texto = ""
    if pct_sev >= 0.5:
        texto += (
            f"- **Viés de severidade**: o LLM classificou `{sev_dominante}` em "
            f"{moda_sev.max()}/{n} casos ({pct_sev:.0%}), independentemente do "
            f"valor de referência. Isso sugere que boa parte do desacordo não é "
            f"ruído aleatório, e sim uma tendência sistemática do LLM em "
            f"convergir para uma única classe de severidade.\n"
        )
    if pct_cat >= 0.5:
        texto += (
            f"- **Viés de categoria**: o LLM classificou `{cat_dominante}` em "
            f"{moda_cat.max()}/{n} casos ({pct_cat:.0%}). Como `combinacao` é a "
            f"categoria natural quando os 3 detectores convergem, isso pode "
            f"refletir o prompt levando o LLM a privilegiar essa opção sempre que "
            f"o texto do caso menciona mais de um sinal, mesmo quando um dos "
            f"sinais é claramente secundário.\n"
        )
    return texto


def gerar_secao_rubrica(resultado: dict) -> str:
    n = resultado["n"]
    return f"""## A) LLM vs. rubrica determinística (n={n})

**Isto NÃO é validação humana.** `reports/rotulos_prelabel.csv` é gerado por
`src/rubric_prelabel.py`, uma regra fixa (ver `reports/criterio_rotulagem.md`)
aplicada sobre os mesmos sinais estatísticos que alimentam o LLM. Esta
comparação mede o quanto o LLM, com um prompt genérico e sem conhecer os
limiares da rubrica, converge para a mesma classificação que uma fórmula
fixa produziria — é um teste de consistência, não de acerto.

Matriz de confusão (linhas = rubrica, colunas = LLM):

{tabela_confusao_md(resultado["confusao"])}

- **Accuracy: {resultado["accuracy"]:.2%}** ({int(resultado["accuracy"] * n)}/{n})
- **Cohen's kappa: {resultado["kappa"]:.3f}**
- **Concordância de categoria: {resultado["concordancia_categoria"]:.2%}** ({int(resultado["concordancia_categoria"] * n)}/{n})

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
{analisar_vies_llm(resultado)}
## B) LLM vs. rotulagem humana genuína (n={resultado["n"]})
"""


def gerar_secao_humano(resultado: dict) -> str:
    n = resultado["n"]
    texto = f"""**{n} caso(s) revisado(s) e rotulado(s) manualmente**, sem seguir a rubrica
escrita — critério do próprio revisor.

Matriz de confusão (linhas = humano, colunas = LLM):

{tabela_confusao_md(resultado["confusao"])}

- **Accuracy: {resultado["accuracy"]:.2%}** ({int(resultado["accuracy"] * n)}/{n})
- **Cohen's kappa: {resultado["kappa"]:.3f}**
- **Concordância de categoria: {resultado["concordancia_categoria"]:.2%}** ({int(resultado["concordancia_categoria"] * n)}/{n})

**Sobre o tamanho da amostra**: n={n} é modesto para accuracy/kappa — ainda
suscetível a mudar de forma notável com mais alguns casos rotulados — mas já
permite ver padrões sistemáticos (não apenas ruído de poucos pontos), ao
contrário de uma amostra n<10.

### Detalhe caso a caso

{tabela_detalhe_md(resultado["merged"], resultado["sev_ref_col"], resultado["cat_ref_col"])}

### Hipóteses para as divergências (humano)

"""
    if resultado["disagreements"].empty:
        texto += f"Nenhuma divergência nos {n} casos rotulados — com essa contagem, isso já é um sinal razoavelmente positivo, mas mais rótulos continuam sendo úteis para confirmar.\n"
    else:
        texto += f"""- Quando os 3 detectores estatísticos sinalizam o mesmo deputado, o LLM
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
{analisar_vies_llm(resultado)}"""
    return texto


def gerar_relatorio(resultado_rubrica: dict, resultado_humano: dict, n_llm: int) -> None:
    conteudo = f"""# Evaluation — Concordância LLM vs. Referências (CEAP)

**Script:** `src/evaluate_llm.py`
**Insumos:** `reports/triage_llm.csv` ({n_llm} casos classificados pelo LLM),
`reports/rotulos_prelabel.csv` (rubrica determinística, n={resultado_rubrica["n"]}),
`reports/rotulos_humanos.csv` (rotulagem humana genuína, n={resultado_humano["n"]})

Este relatório faz **duas comparações distintas e não-intercambiáveis** —
ver `reports/criterio_rotulagem.md` para por que elas não devem ser
confundidas.

"""
    conteudo += gerar_secao_rubrica(resultado_rubrica)
    conteudo += gerar_secao_humano(resultado_humano)
    conteudo += """
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
"""

    destino = REPORTS_DIR / "evaluation_llm.md"
    destino.write_text(conteudo, encoding="utf-8")
    print(f"\nSalvo: {destino}")


def main() -> None:
    llm = pd.read_csv(REPORTS_DIR / "triage_llm.csv", encoding="utf-8")
    rubrica = pd.read_csv(REPORTS_DIR / "rotulos_prelabel.csv", encoding="utf-8-sig")[
        ["txNomeParlamentar", "severidade_prelabel", "categoria_prelabel"]
    ]
    humano = pd.read_csv(REPORTS_DIR / "rotulos_humanos.csv", encoding="utf-8-sig")

    merged_rubrica = carregar_merge(llm, rubrica)
    merged_humano = carregar_merge(llm, humano)

    resultado_rubrica = avaliar(merged_rubrica, "severidade_prelabel", "categoria_prelabel", "Rubrica")
    resultado_humano = avaliar(merged_humano, "severidade_humana", "categoria_humana", "Humano")

    gerar_relatorio(resultado_rubrica, resultado_humano, len(llm))


if __name__ == "__main__":
    main()
