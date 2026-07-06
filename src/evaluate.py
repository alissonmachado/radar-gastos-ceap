"""Evaluation: sensibilidade a limiares, triangulação e amostra para revisão manual (CEAP)."""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

SCORE_THRESHOLDS = [3.0, 3.5, 4.0]
HHI_THRESHOLDS = [0.15, 0.25, 0.35]
RANDOM_STATE = 42


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sensibilidade_limiares(outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame) -> None:
    section("1. Sensibilidade a limiares")

    print("Outliers categoria x pares (score robusto):")
    for t in SCORE_THRESHOLDS:
        n = (outliers_cat["score"].abs() > t).sum()
        print(f"  threshold {t}: {n:,} flags")

    print("\nPicos temporais (score robusto):")
    for t in SCORE_THRESHOLDS:
        n = (picos["score"].abs() > t).sum()
        print(f"  threshold {t}: {n:,} flags")

    print("\nConcentração de fornecedor (HHI):")
    for t in HHI_THRESHOLDS:
        n = (concentracao["hhi"] > t).sum()
        print(f"  threshold {t}: {n:,} flags")


def triangulacao_por_deputado(outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame) -> pd.DataFrame:
    section("2. Triangulação por deputado")

    n_cat = outliers_cat[outliers_cat["flag"]].groupby("txNomeParlamentar").size().rename("n_flags_categoria_pares")
    n_pico = picos[picos["flag"]].groupby("txNomeParlamentar").size().rename("n_flags_pico_temporal")
    conc = concentracao.set_index("txNomeParlamentar")["flag_concentracao_alta"].rename("flag_concentracao_alta")

    max_score_cat = outliers_cat.groupby("txNomeParlamentar")["score"].apply(lambda s: s.abs().max()).rename("max_score_categoria_pares")
    max_score_pico = picos.groupby("txNomeParlamentar")["score"].apply(lambda s: s.abs().max()).rename("max_score_pico_temporal")

    deputados = sorted(
        set(outliers_cat["txNomeParlamentar"])
        | set(picos["txNomeParlamentar"])
        | set(concentracao["txNomeParlamentar"])
    )
    resultado = pd.DataFrame(index=deputados)
    resultado.index.name = "txNomeParlamentar"
    resultado = resultado.join(n_cat).join(n_pico).join(conc).join(max_score_cat).join(max_score_pico)

    resultado["n_flags_categoria_pares"] = resultado["n_flags_categoria_pares"].fillna(0).astype(int)
    resultado["n_flags_pico_temporal"] = resultado["n_flags_pico_temporal"].fillna(0).astype(int)
    resultado["flag_concentracao_alta"] = resultado["flag_concentracao_alta"].fillna(False)

    resultado["n_metodos_distintos"] = (
        (resultado["n_flags_categoria_pares"] > 0).astype(int)
        + (resultado["n_flags_pico_temporal"] > 0).astype(int)
        + resultado["flag_concentracao_alta"].astype(int)
    )
    resultado["max_score_desempate"] = resultado[["max_score_categoria_pares", "max_score_pico_temporal"]].max(axis=1).fillna(0)

    resultado = resultado.sort_values(["n_metodos_distintos", "max_score_desempate"], ascending=False).reset_index()

    n_alta_confianca = (resultado["n_metodos_distintos"] >= 2).sum()
    print(f"Deputados avaliados (aparecem em ao menos 1 detector): {len(resultado):,}")
    print(f"Deputados sinalizados por 2+ métodos distintos (maior confiança): {n_alta_confianca:,}")

    destino = PROCESSED_DIR / "triangulacao_deputados.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(resultado):,} linhas)")

    print("\nTop 15 por nº de métodos distintos:")
    print(
        resultado.head(15)[
            ["txNomeParlamentar", "n_metodos_distintos", "n_flags_categoria_pares", "n_flags_pico_temporal", "flag_concentracao_alta"]
        ].to_string(index=False)
    )

    return resultado


def amostrar(df: pd.DataFrame, coluna_flag: str, n_true: int, n_false: int, detector: str) -> pd.DataFrame:
    flagados = df[df[coluna_flag]]
    nao_flagados = df[~df[coluna_flag]]

    amostra_true = flagados.sample(n=min(n_true, len(flagados)), random_state=RANDOM_STATE)
    amostra_false = nao_flagados.sample(n=min(n_false, len(nao_flagados)), random_state=RANDOM_STATE)

    amostra = pd.concat([amostra_true, amostra_false], ignore_index=True)
    amostra.insert(0, "detector", detector)
    return amostra


def amostra_revisao_manual(outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame) -> None:
    section("3. Amostra para revisão manual")

    a1 = amostrar(outliers_cat, "flag", n_true=15, n_false=10, detector="categoria_pares")
    a2 = amostrar(picos, "flag", n_true=15, n_false=10, detector="pico_temporal")
    a3 = amostrar(concentracao, "flag_concentracao_alta", n_true=10, n_false=5, detector="concentracao_fornecedor")

    amostra = pd.concat([a1, a2, a3], ignore_index=True)
    amostra["rotulo_manual"] = ""
    amostra["comentario"] = ""

    destino = PROCESSED_DIR / "amostra_revisao_manual.csv"
    amostra.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(amostra):,} linhas: {len(a1)} categoria_pares + {len(a2)} pico_temporal + {len(a3)} concentracao_fornecedor)")
    print("Colunas 'rotulo_manual' e 'comentario' deixadas vazias para preenchimento manual.")


def main() -> None:
    outliers_cat = pd.read_csv(PROCESSED_DIR / "outliers_categoria_pares.csv", encoding="utf-8-sig")
    picos = pd.read_csv(PROCESSED_DIR / "picos_temporais.csv", encoding="utf-8-sig")
    concentracao = pd.read_csv(PROCESSED_DIR / "concentracao_fornecedor.csv", encoding="utf-8-sig")

    sensibilidade_limiares(outliers_cat, picos, concentracao)
    triangulacao_por_deputado(outliers_cat, picos, concentracao)
    amostra_revisao_manual(outliers_cat, picos, concentracao)


if __name__ == "__main__":
    main()
