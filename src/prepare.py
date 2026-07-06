"""Data Preparation: limpeza, tipagem e agregações dos dados de Cota Parlamentar (CEAP)."""

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


def cnpj_digits(valor) -> str:
    if pd.isna(valor):
        return ""
    return re.sub(r"\D", "", str(valor))


def limpar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    section("1. Limpeza e tipagem")

    antes_nat = df["datEmissao"].isna().sum()
    df["datEmissao"] = pd.to_datetime(df["datEmissao"], errors="coerce")
    depois_nat = df["datEmissao"].isna().sum()
    print(f"datEmissao -> datetime: {depois_nat - antes_nat:,} valores viraram NaT (não parseáveis)")

    df["cnpjcpf_digits"] = df["txtCNPJCPF"].map(cnpj_digits)

    df["periodo"] = df["numAno"].astype(str) + "-" + df["numMes"].astype(str).str.zfill(2)

    print(f"Coluna 'cnpjcpf_digits' criada (dígitos de txtCNPJCPF).")
    print(f"Coluna 'periodo' criada (YYYY-MM a partir de numAno/numMes).")

    return df


def aplicar_flags(df: pd.DataFrame) -> pd.DataFrame:
    section("2. Flags de qualidade")

    df["flag_estorno"] = df["vlrLiquido"] < 0
    print(f"flag_estorno = True: {df['flag_estorno'].sum():,} registros")

    invalid_codes = {f"{n:014d}" for n in range(INVALID_CNPJ_MIN, INVALID_CNPJ_MAX + 1)}
    cnpj_generico = df["cnpjcpf_digits"].isin(invalid_codes)
    cnpj_ausente = df["cnpjcpf_digits"] == ""
    df["fornecedor_identificado"] = ~(cnpj_generico | cnpj_ausente)

    print(f"fornecedor_identificado = False (CNPJ genérico): {cnpj_generico.sum():,}")
    print(f"fornecedor_identificado = False (CNPJ ausente): {cnpj_ausente.sum():,}")
    print(f"fornecedor_identificado = False (total): {(~df['fornecedor_identificado']).sum():,}")

    return df


def salvar_dataset_limpo(df: pd.DataFrame) -> None:
    section("3. Dataset limpo (linha a linha)")

    destino = PROCESSED_DIR / "despesas_limpas.parquet"
    try:
        df.to_parquet(destino, index=False)
        print(f"Salvo: {destino} ({len(df):,} linhas, {df.shape[1]} colunas)")
    except ImportError:
        destino = PROCESSED_DIR / "despesas_limpas.csv.gz"
        df.to_csv(destino, index=False, encoding="utf-8-sig", compression="gzip")
        print(f"pyarrow indisponível; salvo como CSV: {destino} ({len(df):,} linhas)")


def salvar_agregado(df: pd.DataFrame) -> pd.DataFrame:
    section("4. Agregado deputado x categoria x mês")

    agregado = (
        df.groupby(["txNomeParlamentar", "txtDescricao", "numAno", "numMes"])
        .agg(
            vlrLiquido_total=("vlrLiquido", "sum"),
            n_lancamentos=("vlrLiquido", "count"),
            n_estornos=("flag_estorno", "sum"),
        )
        .reset_index()
        .sort_values(["txNomeParlamentar", "numAno", "numMes"])
    )

    destino = PROCESSED_DIR / "gasto_deputado_categoria_mes.csv"
    agregado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(agregado):,} linhas)")

    return agregado


def main() -> None:
    df = load_data()
    linhas_originais = len(df)

    df = limpar_tipos(df)
    df = aplicar_flags(df)

    section("Checagem: nenhuma linha removida")
    print(f"Linhas originais: {linhas_originais:,} | Linhas no dataset limpo: {len(df):,}")
    assert len(df) == linhas_originais, "Limpeza não deve remover linhas"

    salvar_dataset_limpo(df)
    salvar_agregado(df)


if __name__ == "__main__":
    main()
