"""Perfil inicial (Data Understanding) dos dados de Cota Parlamentar (CEAP)."""

import re
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
FILES = {
    2025: RAW_DIR / "Ano-2025.csv",
    2026: RAW_DIR / "Ano-2026.csv",
}

READ_CSV_KWARGS = dict(sep=";", encoding="utf-8-sig", decimal=".", quotechar='"')

INVALID_CNPJ_MIN = 1
INVALID_CNPJ_MAX = 7


def load_data() -> pd.DataFrame:
    frames = []
    for ano, path in FILES.items():
        df = pd.read_csv(path, **READ_CSV_KWARGS)
        df["_arquivoAno"] = ano
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def profile_shape_and_types(df: pd.DataFrame) -> None:
    section("1. Dimensões, tipos e nulos")
    print(f"Linhas: {len(df):,}")
    print(f"Colunas: {df.shape[1]}")

    perc_nulos = (df.isna().mean() * 100).round(2)
    resumo = pd.DataFrame({"dtype": df.dtypes.astype(str), "% nulos": perc_nulos})
    print(resumo.to_string())


def total_gasto_por_ano(df: pd.DataFrame) -> None:
    section("2. Total gasto (vlrLiquido) por ano")
    total = df.groupby("numAno")["vlrLiquido"].sum().sort_index()
    print(total.map(lambda v: f"R$ {v:,.2f}").to_string())


def top10s(df: pd.DataFrame) -> None:
    section("3. Top 10 deputados por gasto total")
    top_dep = (
        df.groupby("txNomeParlamentar")["vlrLiquido"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_dep.map(lambda v: f"R$ {v:,.2f}").to_string())

    section("3. Top 10 categorias (txtDescricao) por gasto total")
    top_cat = (
        df.groupby("txtDescricao")["vlrLiquido"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_cat.map(lambda v: f"R$ {v:,.2f}").to_string())

    section("3. Top 10 fornecedores (txtFornecedor) por gasto total")
    top_forn = (
        df.groupby("txtFornecedor")["vlrLiquido"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_forn.map(lambda v: f"R$ {v:,.2f}").to_string())


def cnpj_digits(valor) -> str:
    if pd.isna(valor):
        return ""
    return re.sub(r"\D", "", str(valor))


def negativos_e_cnpj_invalido(df: pd.DataFrame) -> None:
    section("4. Registros com vlrLiquido negativo e CNPJ em faixa inválida")

    neg = df[df["vlrLiquido"] < 0]
    print(f"Registros com vlrLiquido negativo: {len(neg):,}")

    digitos = df["txtCNPJCPF"].map(cnpj_digits)
    # CNPJs "genéricos" usados pela Câmara: 00.000.000/0000-01 a 00.000.000/0000-07 (14 dígitos)
    invalid_codes = {f"{n:014d}" for n in range(INVALID_CNPJ_MIN, INVALID_CNPJ_MAX + 1)}
    mask_invalido = digitos.isin(invalid_codes)
    print(f"Registros com CNPJ na faixa inválida (00.000.000/0000-01 a 07): {mask_invalido.sum():,}")

    if mask_invalido.sum() > 0:
        contagem = digitos[mask_invalido].value_counts().sort_index()
        print("\nDetalhe por código:")
        print(contagem.to_string())


def distribuicao_gasto_mensal_por_deputado(df: pd.DataFrame) -> pd.DataFrame:
    section("5. Distribuição do gasto mensal por deputado")

    gasto_mensal = (
        df.groupby(["txNomeParlamentar", "numAno", "numMes"])["vlrLiquido"]
        .sum()
        .reset_index()
    )

    stats = (
        gasto_mensal.groupby("txNomeParlamentar")["vlrLiquido"]
        .agg(media="mean", mediana="median", desvio="std", maximo="max")
        .sort_values("media", ascending=False)
    )

    print("Resumo agregado (estatísticas da distribuição por deputado, todas as médias/medianas/etc.):")
    print(stats.describe().to_string())

    print("\nTop 10 deputados por média de gasto mensal:")
    print(stats.head(10).map(lambda v: f"R$ {v:,.2f}").to_string())

    return stats


def main() -> None:
    df = load_data()

    profile_shape_and_types(df)
    total_gasto_por_ano(df)
    top10s(df)
    negativos_e_cnpj_invalido(df)
    stats = distribuicao_gasto_mensal_por_deputado(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    stats.to_csv(PROCESSED_DIR / "gasto_mensal_por_deputado.csv", encoding="utf-8-sig")


if __name__ == "__main__":
    main()
