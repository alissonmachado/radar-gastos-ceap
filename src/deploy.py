"""Deployment: lista priorizada final de padrões de gasto atípicos (CEAP)."""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

MIN_METODOS_PRIORIDADE = 2


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def maior_caso(df: pd.DataFrame, deputado: str, col_valor: str) -> pd.Series | None:
    casos = df[df["txNomeParlamentar"] == deputado]
    if casos.empty:
        return None
    return casos.loc[casos["score"].abs().idxmax()]


def montar_motivo(deputado: str, outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame) -> str:
    partes = []

    caso_cat = maior_caso(outliers_cat[outliers_cat["flag"]], deputado, "score")
    if caso_cat is not None:
        partes.append(
            f"gasto muito acima dos pares em '{caso_cat['txtDescricao']}' "
            f"({int(caso_cat['numMes']):02d}/{int(caso_cat['numAno'])}, R$ {caso_cat['vlrLiquido_total']:,.2f})"
        )

    caso_pico = maior_caso(picos[picos["flag"]], deputado, "score")
    if caso_pico is not None:
        direcao = "acima" if caso_pico["score"] > 0 else "abaixo"
        partes.append(
            f"mês {direcao} do padrão próprio em {int(caso_pico['numMes']):02d}/{int(caso_pico['numAno'])} "
            f"(R$ {caso_pico['vlrLiquido_total']:,.2f})"
        )

    linha_conc = concentracao[concentracao["txNomeParlamentar"] == deputado]
    if not linha_conc.empty and bool(linha_conc.iloc[0]["flag_concentracao_alta"]):
        c = linha_conc.iloc[0]
        partes.append(
            f"{c['share_fornecedor_top']:.0%} do gasto identificado concentrado em '{c['fornecedor_top']}' (HHI={c['hhi']:.2f})"
        )

    return "; ".join(partes)


def montar_lista_priorizada(
    triangulacao: pd.DataFrame, outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame
) -> pd.DataFrame:
    section("Lista priorizada (deployment)")

    prioridade = triangulacao[triangulacao["n_metodos_distintos"] >= MIN_METODOS_PRIORIDADE].copy()
    prioridade["motivo_resumo"] = prioridade["txNomeParlamentar"].map(
        lambda d: montar_motivo(d, outliers_cat, picos, concentracao)
    )

    resultado = prioridade[
        ["txNomeParlamentar", "n_metodos_distintos", "n_flags_categoria_pares", "n_flags_pico_temporal", "flag_concentracao_alta", "motivo_resumo"]
    ].sort_values(["n_metodos_distintos", "txNomeParlamentar"], ascending=[False, True])

    print(f"Deputados com prioridade alta (>= {MIN_METODOS_PRIORIDADE} métodos distintos): {len(resultado):,}")

    destino = REPORTS_DIR / "lista_priorizada.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Salvo: {destino} ({len(resultado):,} linhas)")

    print("\nTop 10:")
    print(resultado.head(10).to_string(index=False))

    return resultado


def main() -> None:
    triangulacao = pd.read_csv(PROCESSED_DIR / "triangulacao_deputados.csv", encoding="utf-8-sig")
    outliers_cat = pd.read_csv(PROCESSED_DIR / "outliers_categoria_pares.csv", encoding="utf-8-sig")
    picos = pd.read_csv(PROCESSED_DIR / "picos_temporais.csv", encoding="utf-8-sig")
    concentracao = pd.read_csv(PROCESSED_DIR / "concentracao_fornecedor.csv", encoding="utf-8-sig")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    montar_lista_priorizada(triangulacao, outliers_cat, picos, concentracao)


if __name__ == "__main__":
    main()
