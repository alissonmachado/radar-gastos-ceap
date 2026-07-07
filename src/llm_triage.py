"""LLM Triage: classificação e explicação dos casos priorizados via API Anthropic + Pydantic (CEAP).

Recebe os casos JÁ detectados estatisticamente (deploy.py) e pede ao LLM apenas
classificar severidade, tipificar o padrão e explicar em linguagem cidadã.
O LLM nunca decide o que é anômalo nem afirma irregularidade (regras 3 e 4 do CLAUDE.md).

Uso:
    python src/llm_triage.py            # top 50 casos (default)
    python src/llm_triage.py --top 15   # controla custo
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 2  # 1 tentativa + 1 retry com feedback do erro

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Schema Pydantic (regra 4 do CLAUDE.md: toda saída de LLM é validada)
# ---------------------------------------------------------------------------
class TriageAnomalia(BaseModel):
    severidade: Literal["baixa", "media", "alta"] = Field(
        description="Urgência de verificação humana, dada a magnitude e convergência dos sinais"
    )
    categoria_anomalia: Literal[
        "concentracao_fornecedor", "pico_temporal", "gasto_acima_pares", "combinacao"
    ] = Field(description="Tipo dominante do padrão detectado")
    explicacao_cidada: str = Field(
        max_length=280,
        description="Explicação em linguagem simples do padrão numérico, SEM acusação",
    )
    perguntas_auditoria: list[str] = Field(
        min_length=2, max_length=3,
        description="Perguntas objetivas que um auditor/jornalista deveria verificar",
    )


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


def montar_caso(row: pd.Series) -> str:
    """Serializa uma linha da lista priorizada como texto factual para o LLM."""
    partes = [
        f"Parlamentar: {row['txNomeParlamentar']}",
        f"Métodos estatísticos que sinalizaram (0-3): {row['n_metodos_distintos']}",
        f"Resumo dos sinais detectados: {row['motivo_resumo']}",
    ]
    return "\n".join(partes)


def classificar(client: Anthropic, caso: str) -> tuple[TriageAnomalia | None, str]:
    """Chama a API e valida com Pydantic. Retorna (resultado, status)."""
    feedback = ""
    for tentativa in range(1, MAX_RETRIES + 1):
        prompt = USER_PROMPT_TEMPLATE.format(caso=caso) + feedback
        resposta = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in resposta.content if b.type == "text").strip()
        # tolera cercas de código apesar da instrução
        texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            dados = json.loads(texto)
            return TriageAnomalia.model_validate(dados), f"ok_tentativa_{tentativa}"
        except (json.JSONDecodeError, ValidationError) as e:
            feedback = (
                "\n\nSua resposta anterior falhou na validação com o erro abaixo. "
                f"Corrija e responda apenas o JSON válido:\n{e}"
            )
    return None, "nao_classificado"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=50, help="quantos casos enviar ao LLM (controle de custo)")
    args = parser.parse_args()

    client = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente (.env)

    lista = pd.read_csv(REPORTS_DIR / "lista_priorizada.csv")
    casos = lista.head(args.top).copy()
    print(f"Enviando {len(casos)} casos ao modelo {MODEL}...")

    resultados = []
    for i, (_, row) in enumerate(casos.iterrows(), start=1):
        triage, status = classificar(client, montar_caso(row))
        registro = {
            "txNomeParlamentar": row["txNomeParlamentar"],
            "n_metodos_distintos": row["n_metodos_distintos"],
            "status_llm": status,
        }
        if triage is not None:
            registro.update(triage.model_dump())
            registro["perguntas_auditoria"] = " | ".join(triage.perguntas_auditoria)
        resultados.append(registro)
        print(f"  [{i}/{len(casos)}] {row['txNomeParlamentar']}: {status}")

    df = pd.DataFrame(resultados)
    saida = REPORTS_DIR / "triage_llm.csv"
    df.to_csv(saida, index=False)

    print("\nResumo:")
    print(df["status_llm"].value_counts().to_string())
    if "severidade" in df.columns:
        print("\nSeveridade atribuída:")
        print(df["severidade"].value_counts().to_string())
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    main()