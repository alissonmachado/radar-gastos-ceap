"""Modeling: detecção estatística de padrões de gasto atípicos (CEAP)."""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
DESPESAS_LIMPAS = PROCESSED_DIR / "despesas_limpas.parquet"
GASTO_CATEGORIA_MES = PROCESSED_DIR / "gasto_deputado_categoria_mes.csv"

SCORE_THRESHOLD = 3.5
MIN_PARES_GRUPO = 5
MIN_MESES_HISTORICO = 6
MIN_GASTO_IDENTIFICADO = 1000.0
HHI_THRESHOLD = 0.25


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def robust_z(x: pd.Series) -> pd.Series:
    mediana = x.median()
    mad = (x - mediana).abs().median()
    escala = mad if mad > 0 else 1e-6 * (abs(mediana) + 1)
    return 0.6745 * (x - mediana) / escala


def outliers_categoria_pares(gasto_cat_mes: pd.DataFrame) -> pd.DataFrame:
    section("1. Outliers por categoria x mês vs. pares")

    grupos = gasto_cat_mes.groupby(["txtDescricao", "numAno", "numMes"])
    tamanhos = grupos["txNomeParlamentar"].transform("size")
    validos = gasto_cat_mes[tamanhos >= MIN_PARES_GRUPO].copy()
    pulados = gasto_cat_mes[tamanhos < MIN_PARES_GRUPO]

    print(f"Grupos (categoria x mês) avaliados: {gasto_cat_mes.groupby(['txtDescricao', 'numAno', 'numMes']).ngroups:,}")
    print(f"Registros em grupos pequenos (<{MIN_PARES_GRUPO} deputados), pulados: {len(pulados):,}")

    validos["mediana_pares"] = validos.groupby(["txtDescricao", "numAno", "numMes"])["vlrLiquido_total"].transform("median")
    validos["mad_pares"] = validos.groupby(["txtDescricao", "numAno", "numMes"])["vlrLiquido_total"].transform(
        lambda x: (x - x.median()).abs().median()
    )
    validos["score"] = validos.groupby(["txtDescricao", "numAno", "numMes"])["vlrLiquido_total"].transform(robust_z)
    validos["flag"] = validos["score"].abs() > SCORE_THRESHOLD

    print(f"Flags geradas: {validos['flag'].sum():,}")

    resultado = validos[
        [
            "txNomeParlamentar",
            "txtDescricao",
            "numAno",
            "numMes",
            "vlrLiquido_total",
            "mediana_pares",
            "mad_pares",
            "score",
            "flag",
        ]
    ].sort_values("score", key=lambda s: s.abs(), ascending=False)

    destino = PROCESSED_DIR / "outliers_categoria_pares.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(resultado):,} linhas)")

    print("\nTop 10 por |score|:")
    print(
        resultado.head(10)[["txNomeParlamentar", "txtDescricao", "numAno", "numMes", "vlrLiquido_total", "score", "flag"]]
        .to_string(index=False)
    )

    return resultado


def concentracao_fornecedor(despesas: pd.DataFrame) -> pd.DataFrame:
    section("2. Concentração em fornecedor único (HHI)")

    identificadas = despesas[despesas["fornecedor_identificado"]]

    por_fornecedor = (
        identificadas.groupby(["txNomeParlamentar", "txtFornecedor"])["vlrLiquido"]
        .sum()
        .reset_index()
    )
    totais = por_fornecedor.groupby("txNomeParlamentar")["vlrLiquido"].sum().rename("total_identificado")
    por_fornecedor = por_fornecedor.merge(totais, on="txNomeParlamentar")
    por_fornecedor["share"] = por_fornecedor["vlrLiquido"] / por_fornecedor["total_identificado"]

    hhi = por_fornecedor.groupby("txNomeParlamentar").apply(
        lambda g: (g["share"] ** 2).sum(), include_groups=False
    ).rename("hhi")

    top_fornecedor_idx = por_fornecedor.groupby("txNomeParlamentar")["share"].idxmax()
    top_fornecedor = por_fornecedor.loc[
        top_fornecedor_idx, ["txNomeParlamentar", "txtFornecedor", "share"]
    ].rename(columns={"txtFornecedor": "fornecedor_top", "share": "share_fornecedor_top"})

    resultado = (
        hhi.reset_index()
        .merge(top_fornecedor, on="txNomeParlamentar")
        .merge(totais.reset_index(), on="txNomeParlamentar")
    )
    resultado = resultado[resultado["total_identificado"] >= MIN_GASTO_IDENTIFICADO]
    resultado["flag_concentracao_alta"] = resultado["hhi"] > HHI_THRESHOLD
    resultado = resultado.sort_values("hhi", ascending=False)

    print(f"Deputados avaliados (gasto identificado >= R$ {MIN_GASTO_IDENTIFICADO:,.2f}): {len(resultado):,}")
    print(f"Flags geradas (HHI > {HHI_THRESHOLD}): {resultado['flag_concentracao_alta'].sum():,}")

    destino = PROCESSED_DIR / "concentracao_fornecedor.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(resultado):,} linhas)")

    print("\nTop 10 por HHI:")
    print(
        resultado.head(10)[
            ["txNomeParlamentar", "hhi", "fornecedor_top", "share_fornecedor_top", "total_identificado", "flag_concentracao_alta"]
        ].to_string(index=False)
    )

    return resultado


def picos_temporais(gasto_cat_mes: pd.DataFrame) -> pd.DataFrame:
    section("3. Picos pontuais no tempo (histórico próprio)")

    gasto_mes = (
        gasto_cat_mes.groupby(["txNomeParlamentar", "numAno", "numMes"])["vlrLiquido_total"]
        .sum()
        .reset_index()
    )

    tamanhos = gasto_mes.groupby("txNomeParlamentar")["numMes"].transform("size")
    validos = gasto_mes[tamanhos >= MIN_MESES_HISTORICO].copy()
    pulados_deputados = gasto_mes.loc[tamanhos < MIN_MESES_HISTORICO, "txNomeParlamentar"].nunique()

    print(f"Deputados avaliados (>= {MIN_MESES_HISTORICO} meses de histórico): {validos['txNomeParlamentar'].nunique():,}")
    print(f"Deputados pulados (histórico curto): {pulados_deputados:,}")

    validos["mediana_propria"] = validos.groupby("txNomeParlamentar")["vlrLiquido_total"].transform("median")
    validos["mad_propria"] = validos.groupby("txNomeParlamentar")["vlrLiquido_total"].transform(
        lambda x: (x - x.median()).abs().median()
    )
    validos["score"] = validos.groupby("txNomeParlamentar")["vlrLiquido_total"].transform(robust_z)
    validos["flag"] = validos["score"].abs() > SCORE_THRESHOLD

    print(f"Flags geradas: {validos['flag'].sum():,}")

    resultado = validos[
        ["txNomeParlamentar", "numAno", "numMes", "vlrLiquido_total", "mediana_propria", "mad_propria", "score", "flag"]
    ].sort_values("score", key=lambda s: s.abs(), ascending=False)

    destino = PROCESSED_DIR / "picos_temporais.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(resultado):,} linhas)")

    print("\nTop 10 por |score|:")
    print(
        resultado.head(10)[["txNomeParlamentar", "numAno", "numMes", "vlrLiquido_total", "score", "flag"]]
        .to_string(index=False)
    )

    return resultado


def main() -> None:
    gasto_cat_mes = pd.read_csv(GASTO_CATEGORIA_MES, encoding="utf-8-sig")
    despesas = pd.read_parquet(DESPESAS_LIMPAS)

    outliers_categoria_pares(gasto_cat_mes)
    concentracao_fornecedor(despesas)
    picos_temporais(gasto_cat_mes)


if __name__ == "__main__":
    main()
