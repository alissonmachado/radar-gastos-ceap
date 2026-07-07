"""Pré-rotulagem determinística por rubrica dos casos priorizados (CEAP).

Aplica uma regra fixa (sem LLM, sem julgamento subjetivo) sobre os sinais já
calculados nas fases de Modeling/Evaluation, para acelerar a revisão humana —
não substitui o rótulo humano, apenas sugere um ponto de partida auditável.
"""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"

N_CASOS = 50

# Mesmos limiares de src/model.py — usados para normalizar "quão além do
# limiar" cada sinal está, ao decidir qual é o dominante.
SCORE_THRESHOLD = 3.5
HHI_THRESHOLD = 0.25

SEVERIDADE_ALTA_VALOR = 50_000
SEVERIDADE_ALTA_HHI = 0.5
SEVERIDADE_ALTA_N_FLAGS = 5
SEVERIDADE_BAIXA_VALOR = 10_000
MESES_PARCIAIS = {(2026, 6), (2026, 7)}


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def maior_caso_flagado(df_flagado: pd.DataFrame, deputado: str) -> pd.Series | None:
    casos = df_flagado[df_flagado["txNomeParlamentar"] == deputado]
    if casos.empty:
        return None
    return casos.loc[casos["score"].abs().idxmax()]


def fmt_valor(v: float) -> str:
    return f"R$ {v:,.2f}"


def montar_sinal_resumo(caso_cat, caso_pico, linha_conc) -> str:
    partes = []
    if caso_cat is not None:
        partes.append(
            f"categoria '{caso_cat['txtDescricao']}' score={caso_cat['score']:.2f} "
            f"({fmt_valor(caso_cat['vlrLiquido_total'])} em {int(caso_cat['numMes']):02d}/{int(caso_cat['numAno'])})"
        )
    if caso_pico is not None:
        partes.append(
            f"pico score={caso_pico['score']:.2f} "
            f"({fmt_valor(caso_pico['vlrLiquido_total'])} em {int(caso_pico['numMes']):02d}/{int(caso_pico['numAno'])})"
        )
    if linha_conc is not None:
        partes.append(
            f"hhi={linha_conc['hhi']:.2f} (fornecedor: {linha_conc['fornecedor_top']})"
        )
    return "; ".join(partes) if partes else "sem sinal detalhado disponível"


def classificar_severidade(sinal_valor: float, hhi: float, n_flags_total: int, pico_unico_queda_parcial: bool, fornecedor_facebook: bool) -> str:
    if sinal_valor >= SEVERIDADE_ALTA_VALOR or hhi >= SEVERIDADE_ALTA_HHI or n_flags_total >= SEVERIDADE_ALTA_N_FLAGS:
        return "alta"
    if sinal_valor < SEVERIDADE_BAIXA_VALOR or fornecedor_facebook or pico_unico_queda_parcial:
        return "baixa"
    return "media"


def classificar_categoria(flagged_cat: bool, flagged_pico: bool, flagged_conc: bool, ratio_cat: float, ratio_pico: float, ratio_conc: float) -> str:
    if flagged_cat and flagged_pico and flagged_conc:
        return "combinacao"

    candidatos = []
    if flagged_cat:
        candidatos.append(("gasto_acima_pares", ratio_cat))
    if flagged_pico:
        candidatos.append(("pico_temporal", ratio_pico))
    if flagged_conc:
        candidatos.append(("concentracao_fornecedor", ratio_conc))

    # desempate por ordem de prioridade fixa: categoria_pares > pico_temporal > concentracao_fornecedor
    candidatos.sort(key=lambda c: c[1], reverse=True)
    return candidatos[0][0]


def processar(lista: pd.DataFrame, outliers_cat: pd.DataFrame, picos: pd.DataFrame, concentracao: pd.DataFrame) -> pd.DataFrame:
    section(f"Pré-rotulagem por rubrica ({N_CASOS} primeiros casos)")

    cat_flagados = outliers_cat[outliers_cat["flag"]]
    pico_flagados = picos[picos["flag"]]

    linhas = []
    inconsistencias = 0

    for _, row in lista.iterrows():
        deputado = row["txNomeParlamentar"]

        caso_cat = maior_caso_flagado(cat_flagados, deputado)
        caso_pico = maior_caso_flagado(pico_flagados, deputado)
        conc_rows = concentracao[concentracao["txNomeParlamentar"] == deputado]
        linha_conc = conc_rows.iloc[0] if not conc_rows.empty else None

        flagged_cat = row["n_flags_categoria_pares"] > 0
        flagged_pico = row["n_flags_pico_temporal"] > 0
        flagged_conc = bool(row["flag_concentracao_alta"])

        if int(flagged_cat) + int(flagged_pico) + int(flagged_conc) != row["n_metodos_distintos"]:
            inconsistencias += 1

        hhi = float(linha_conc["hhi"]) if linha_conc is not None else 0.0
        fornecedor_top = linha_conc["fornecedor_top"] if linha_conc is not None else None
        fornecedor_facebook = isinstance(fornecedor_top, str) and "facebook" in fornecedor_top.lower()

        valores = [c["vlrLiquido_total"] for c in (caso_cat, caso_pico) if c is not None]
        sinal_valor = max(valores) if valores else 0.0

        pico_unico_queda_parcial = (
            row["n_flags_pico_temporal"] == 1
            and caso_pico is not None
            and caso_pico["score"] < 0
            and (int(caso_pico["numAno"]), int(caso_pico["numMes"])) in MESES_PARCIAIS
        )

        n_flags_total = row["n_flags_categoria_pares"] + row["n_flags_pico_temporal"]

        severidade = classificar_severidade(sinal_valor, hhi, n_flags_total, pico_unico_queda_parcial, fornecedor_facebook)

        ratio_cat = abs(caso_cat["score"]) / SCORE_THRESHOLD if caso_cat is not None else 0.0
        ratio_pico = abs(caso_pico["score"]) / SCORE_THRESHOLD if caso_pico is not None else 0.0
        ratio_conc = hhi / HHI_THRESHOLD if linha_conc is not None else 0.0

        categoria = classificar_categoria(flagged_cat, flagged_pico, flagged_conc, ratio_cat, ratio_pico, ratio_conc)

        linhas.append(
            {
                "txNomeParlamentar": deputado,
                "sinal_resumo": montar_sinal_resumo(caso_cat, caso_pico, linha_conc),
                "severidade_prelabel": severidade,
                "categoria_prelabel": categoria,
                "severidade_humana": "",
                "categoria_humana": "",
            }
        )

    if inconsistencias:
        print(f"AVISO: {inconsistencias} casos com n_metodos_distintos inconsistente com as flags individuais.")

    resultado = pd.DataFrame(linhas)

    print(f"Casos processados: {len(resultado):,}")
    print("\nDistribuição severidade_prelabel:")
    print(resultado["severidade_prelabel"].value_counts().to_string())
    print("\nDistribuição categoria_prelabel:")
    print(resultado["categoria_prelabel"].value_counts().to_string())

    destino = REPORTS_DIR / "rotulos_prelabel.csv"
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"\nSalvo: {destino} ({len(resultado):,} linhas, colunas severidade_humana/categoria_humana vazias)")

    return resultado


def main() -> None:
    lista = pd.read_csv(REPORTS_DIR / "lista_priorizada.csv", encoding="utf-8-sig").head(N_CASOS)
    outliers_cat = pd.read_csv(PROCESSED_DIR / "outliers_categoria_pares.csv", encoding="utf-8-sig")
    picos = pd.read_csv(PROCESSED_DIR / "picos_temporais.csv", encoding="utf-8-sig")
    concentracao = pd.read_csv(PROCESSED_DIR / "concentracao_fornecedor.csv", encoding="utf-8-sig")

    processar(lista, outliers_cat, picos, concentracao)


if __name__ == "__main__":
    main()
