"""Estima o custo real (em tokens e USD) do src/llm_triage.py.

Usa client.messages.count_tokens (endpoint gratuito, não gera resposta) sobre os
prompts realmente enviados e sobre as respostas realmente recebidas (já salvas em
reports/triage_llm.csv), para não precisar refazer as chamadas pagas de geração.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
load_dotenv(BASE_DIR / ".env")

MODEL = "claude-sonnet-4-6"
# Pricing oficial (cache 2026-06-24, via skill claude-api): claude-sonnet-4-6
PRECO_INPUT_POR_MILHAO = 3.00
PRECO_OUTPUT_POR_MILHAO = 15.00

SYSTEM_PROMPT = """Você é um assistente de triagem de dados públicos da Cota Parlamentar (CEAP).

Você recebe padrões de gasto JÁ detectados por métodos estatísticos. Sua função é
APENAS classificar e explicar — nunca julgar pessoas.

Regras absolutas:
1. NUNCA afirme ou insinue irregularidade, fraude, corrupção ou má-fé. Padrões
   atípicos têm com frequência explicações legítimas (campanhas de divulgação,
   contratos anuais, distância do estado, funções de liderança).
2. Descreva apenas o padrão numérico e o que verificar. Ex.: "o gasto de X na
   categoria Y foi N vezes a mediana dos colegas no mês" — nunca "gasto suspeito".
3. explicacao_cidada: linguagem simples, sem jargão estatístico (não use "MAD",
   "z-score", "HHI" — traduza: "muito acima do típico", "concentrado em um único
   fornecedor").
4. perguntas_auditoria: perguntas verificáveis e neutras (ex.: "Os serviços
   contratados do fornecedor Z têm notas fiscais com descrição detalhada?").
5. Responda SOMENTE com JSON válido no schema pedido. Sem markdown, sem texto
   antes ou depois, sem cercas de código."""

USER_PROMPT_TEMPLATE = """Caso detectado estatisticamente (dados oficiais CEAP 2025-2026):

{caso}

Responda SOMENTE com um JSON com estes campos:
- "severidade": "baixa" | "media" | "alta"
- "categoria_anomalia": "concentracao_fornecedor" | "pico_temporal" | "gasto_acima_pares" | "combinacao"
- "explicacao_cidada": string com no máximo 280 caracteres, linguagem simples, sem acusação
- "perguntas_auditoria": lista de 2 a 3 strings"""


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def montar_caso(row: pd.Series) -> str:
    partes = [
        f"Parlamentar: {row['txNomeParlamentar']}",
        f"Métodos estatísticos que sinalizaram (0-3): {row['n_metodos_distintos']}",
        f"Resumo dos sinais detectados: {row['motivo_resumo']}",
    ]
    return "\n".join(partes)


def montar_resposta_json(row: pd.Series) -> str:
    return json.dumps(
        {
            "severidade": row["severidade"],
            "categoria_anomalia": row["categoria_anomalia"],
            "explicacao_cidada": row["explicacao_cidada"],
            "perguntas_auditoria": row["perguntas_auditoria"].split(" | "),
        },
        ensure_ascii=False,
    )


def main() -> None:
    client = Anthropic()

    lista = pd.read_csv(REPORTS_DIR / "lista_priorizada.csv", encoding="utf-8-sig")
    triage = pd.read_csv(REPORTS_DIR / "triage_llm.csv", encoding="utf-8")

    merged = triage.merge(lista[["txNomeParlamentar", "motivo_resumo"]], on="txNomeParlamentar", how="left")
    n = len(merged)

    section(f"Contagem real de tokens via count_tokens ({n} casos, modelo {MODEL})")

    total_input = 0
    total_output = 0

    for i, row in merged.iterrows():
        prompt = USER_PROMPT_TEMPLATE.format(caso=montar_caso(row))
        contagem_input = client.messages.count_tokens(
            model=MODEL,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        total_input += contagem_input.input_tokens

        resposta_json = montar_resposta_json(row)
        contagem_output = client.messages.count_tokens(
            model=MODEL,
            messages=[{"role": "user", "content": resposta_json}],
        )
        total_output += contagem_output.input_tokens

        if (i + 1) % 10 == 0:
            print(f"  [{i + 1}/{n}] processados")

    custo_input = total_input / 1_000_000 * PRECO_INPUT_POR_MILHAO
    custo_output = total_output / 1_000_000 * PRECO_OUTPUT_POR_MILHAO
    custo_total = custo_input + custo_output

    print(f"\nTotal tokens de input (real, via count_tokens): {total_input:,}")
    print(f"Total tokens de output (estimado a partir da resposta real): {total_output:,}")
    print(f"Custo input:  US$ {custo_input:.4f}  (US$ {PRECO_INPUT_POR_MILHAO:.2f}/milhão)")
    print(f"Custo output: US$ {custo_output:.4f}  (US$ {PRECO_OUTPUT_POR_MILHAO:.2f}/milhão)")
    print(f"Custo total ({n} casos): US$ {custo_total:.4f}")
    print(f"Custo médio por caso: US$ {custo_total / n:.5f}")

    # Projeção para os 253 casos priorizados (n_metodos_distintos >= 2)
    projecao_253 = (custo_total / n) * 253
    print(f"\nProjeção linear para os 253 casos priorizados: US$ {projecao_253:.2f}")

    resultado = {
        "modelo": MODEL,
        "n_casos": n,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "preco_input_por_milhao_usd": PRECO_INPUT_POR_MILHAO,
        "preco_output_por_milhao_usd": PRECO_OUTPUT_POR_MILHAO,
        "custo_input_usd": round(custo_input, 4),
        "custo_output_usd": round(custo_output, 4),
        "custo_total_usd": round(custo_total, 4),
        "custo_medio_por_caso_usd": round(custo_total / n, 5),
        "projecao_253_casos_usd": round(projecao_253, 2),
    }
    destino = REPORTS_DIR / "custo_llm_triage.json"
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo: {destino}")


if __name__ == "__main__":
    main()
