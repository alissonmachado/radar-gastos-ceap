# Relatório Final — Radar de Gastos da Cota Parlamentar (CEAP)

## O que é isso

A Cota para o Exercício da Atividade Parlamentar (CEAP) é o valor mensal que
cada deputado federal recebe para custear despesas ligadas ao mandato:
passagens, combustível, divulgação do trabalho parlamentar, manutenção de
escritório, entre outras. Os dados são públicos e atualizados diariamente
pela Câmara dos Deputados.

Este projeto analisou **284.845 despesas** registradas em 2025 e 2026
(R$ 242,2 milhões em 2025 e R$ 102,9 milhões em 2026, ano ainda parcial) para
**priorizar** — nunca acusar — casos em que o padrão de gasto foge do
esperado e merece um olhar mais atento de cidadãos, jornalistas ou
auditores. Sinalizar um caso aqui não significa irregularidade: significa
apenas que ele é estatisticamente incomum e vale a pena entender o porquê.

## Como chegamos aqui

O trabalho seguiu quatro etapas:

1. **Entendimento dos dados**: mapeamos o volume, os tipos de cada coluna e
   os principais problemas de qualidade (ver `reports/data_understanding.md`).
2. **Preparação**: corrigimos tipos (datas, CNPJ), e sinalizamos sem excluir
   duas situações especiais — despesas com valor negativo (estornos) e
   despesas com CNPJ genérico (sem fornecedor identificável).
3. **Modelagem**: comparamos cada deputado de três formas independentes —
   contra outros deputados na mesma categoria de despesa e mês; contra o
   próprio histórico de gastos mensais; e pela concentração do gasto num
   único fornecedor.
4. **Avaliação**: verificamos se esses três "olhares" concordam entre si
   (quando 2 ou mais apontam o mesmo deputado, a suspeita de anomalia real é
   mais forte) e preparamos uma amostra para conferência manual futura.

## Lista priorizada

De 601 deputados analisados, **253 foram sinalizados por 2 ou mais dos 3
métodos** (lista completa em `reports/lista_priorizada.csv`). Destes,
**26 foram sinalizados pelos 3 métodos ao mesmo tempo** — o grupo de maior
prioridade:

| Deputado | Motivo resumido |
|---|---|
| Aguinaldo Ribeiro | Passagem aérea muito acima dos pares (06/2025); mês de pico em 06/2025; 46% do gasto identificado num único fornecedor |
| Benedita da Silva | Hospedagem muito acima dos pares (11/2025); mês muito abaixo do próprio padrão (07/2026); 56% concentrado num fornecedor |
| Bruno Ganem | Assinatura de publicações fora do padrão (08/2025); pico em 06/2025; 55% concentrado num fornecedor |
| Célio Silveira | Divulgação parlamentar muito acima dos pares (07/2025, R$ 95 mil); pico no mesmo mês; 60% concentrado num fornecedor |
| Elcione Barbalho | Divulgação parlamentar acima dos pares (06/2026); pico no mesmo mês; 62% concentrado num fornecedor |
| Ely Santos | Divulgação parlamentar acima dos pares (05/2025); pico no mesmo mês; 41% concentrado num fornecedor |
| Erika Kokay | Táxi/pedágio fora do padrão (04/2026); mês muito abaixo do próprio padrão (07/2026); 55% concentrado num fornecedor |
| Fabio Schiochet | Hospedagem acima dos pares (03/2025); pico em 12/2025; 49% concentrado num fornecedor |
| Gabriel Mota | Manutenção de escritório acima dos pares (04/2026); 75% concentrado num único fornecedor (maior HHI do grupo) |
| Gilson Marques | Hospedagem acima dos pares (12/2025); pico em 07/2025; 63% concentrado num fornecedor |
| Henderson Pinto | Passagem aérea acima dos pares (01/2025); mês abaixo do próprio padrão (06/2026); 49% concentrado num fornecedor |
| Jeferson Rodrigues | Divulgação parlamentar acima dos pares (04/2026); pico no mesmo mês; 55% concentrado num fornecedor |
| Josenildo | Serviço de segurança acima dos pares (04/2025); mês muito abaixo do padrão (07/2026); 53% concentrado num fornecedor |
| Liderança do União Brasil | Fornecimento de alimentação acima dos pares (04/2026); pico no mesmo mês; 47% concentrado num fornecedor |
| Magda Mofatto | Manutenção de escritório acima dos pares (01/2026); mês abaixo do padrão (11/2025); 44% concentrado num fornecedor |
| Marcos Tavares | Manutenção de escritório acima dos pares (06/2026); 40% concentrado num fornecedor |
| Marx Beltrão | Passagem aérea acima dos pares (02/2026); pico em 03/2026; 46% concentrado num fornecedor |
| Mauricio do Vôlei | Divulgação parlamentar acima dos pares (05/2026); pico no mesmo mês; 45% concentrado num fornecedor |
| Maurício Carvalho | Hospedagem acima dos pares (10/2025); mês abaixo do padrão (06/2026); 42% concentrado num fornecedor |
| Olival Marques | Divulgação parlamentar acima dos pares (04/2025); pico no mesmo mês; 39% concentrado num fornecedor |
| Otoni de Paula | Telefonia fora do padrão (01/2025); pico em 07/2025 (R$ 76 mil); 55% concentrado num fornecedor |
| Pastor Gil | Divulgação parlamentar acima dos pares (12/2025, R$ 92 mil); pico no mesmo mês; 47% concentrado num fornecedor |
| Professor Alcides | Manutenção de escritório acima dos pares (03/2026); mês abaixo do padrão (12/2025); 47% concentrado num fornecedor |
| Sargento Gonçalves | Divulgação parlamentar muito acima dos pares (10/2025, R$ 141 mil); pico em 12/2025; 56% concentrado num fornecedor |
| Soraya Santos | Divulgação parlamentar acima dos pares (08/2025); pico em 04/2025; 35% concentrado num fornecedor |
| Sâmia Bomfim | Serviço de segurança fora do padrão (05/2026); pico em 04/2025; 40% concentrado num fornecedor |

*Valores e datas completos em `reports/lista_priorizada.csv`; os outros 227
casos com 2 métodos convergentes também estão lá.*

## O que isso NÃO significa

- **Não é acusação.** É um ranking estatístico de prioridade para
  investigação, não uma conclusão sobre irregularidade.
- **Contas de liderança partidária** (ex. "Liderança do União Brasil")
  aparecem nas comparações por categoria/mês, mas têm padrão de uso da cota
  diferente de um deputado individual — a comparação com "pares" é menos
  direta nesses casos.
- **2026 é um ano parcial** (dados só até meados do ano), o que pode
  distorcer tanto a comparação por categoria/mês quanto o histórico próprio
  de um deputado.
- **Nenhum caso foi validado por revisão humana ainda.** A fase de Avaliação
  gerou uma amostra (`data/processed/amostra_revisao_manual.csv`, 65 casos)
  especificamente para isso, mas o rótulo manual ainda não foi preenchido.

## Limitações técnicas

- Despesas com CNPJ genérico ou ausente (45.635 registros, ~16% do total)
  foram excluídas apenas do cálculo de concentração de fornecedor (HHI);
  continuam somadas nos totais e nas outras duas detecções.
- Quando a maioria dos pares/meses tem valores idênticos, a medida de
  dispersão (MAD) pode ser zero; usamos um valor mínimo artificial para
  evitar divisão por zero, o que pode inflar levemente o score nesses casos
  raros.
- Sem rótulo humano (ground-truth), não é possível calcular métricas de
  precisão/revocação do método — a análise de sensibilidade a limiares
  (`reports/../data/processed/` na fase de Evaluation) mostra que o volume de
  casos sinalizados é razoavelmente estável a variações do limiar, mas isso
  não substitui validação manual.

## Plano de atualização

A Câmara atualiza os arquivos `Ano-{ano}.csv.zip` diariamente. Não é
necessário reprocessar com essa frequência — uma cadência mensal ou
trimestral é suficiente para acompanhar o mandato. Para atualizar:

1. Baixar os arquivos mais recentes para `data/raw/` (ver `README.md`).
2. Rodar o pipeline completo, na ordem: `explore.py` → `prepare.py` →
   `model.py` → `evaluate.py` → `deploy.py`.
3. Revisar se os limiares (`SCORE_THRESHOLD = 3.5`, `HHI_THRESHOLD = 0.25`
   em `src/model.py`) continuam adequados à luz da análise de sensibilidade
   feita em `src/evaluate.py` — o volume de flags pode crescer conforme mais
   dados de 2026 chegam.

## Próximos passos possíveis (fora do escopo atual)

- Preencher os rótulos manuais em `amostra_revisao_manual.csv` para medir a
  taxa real de falsos positivos.
- Uma eventual etapa de triagem por LLM para classificar/explicar os casos
  em linguagem ainda mais acessível — não implementada nesta versão.
- Um painel interativo (dashboard) para explorar a lista priorizada.
