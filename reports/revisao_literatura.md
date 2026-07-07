# Revisão da Literatura

O precedente direto deste trabalho, no mesmo domínio (gastos CEAP), é a
**Operação Serenata de Amor** [@musskopf2016serenata]: projeto open-source
iniciado em 2016 por Irio Musskopf e Eduardo Cuducos que usa um robô de
aprendizado de máquina ("Rosie") para calcular uma probabilidade de
irregularidade em reembolsos da Cota Parlamentar e publicar os achados. Este
trabalho se diferencia em três pontos: (i) usa detecção estatística robusta
(mediana/MAD) como camada auditável antes de qualquer classificação, em vez
de um único score de probabilidade; (ii) usa um LLM apenas para classificar
e explicar em linguagem cidadã os casos já sinalizados estatisticamente —
nunca para decidir sozinho o que é atípico; e (iii) inclui triangulação
entre métodos independentes e avaliação de concordância humano-LLM (Cohen's
kappa) como camada explícita de validação, ausente na Rosie original.

A camada estatística deste trabalho segue **Iglewicz & Hoaglin (1993)**
[@iglewicz1993outliers]: mediana e desvio absoluto mediano (MAD) como
medidas robustas de tendência central e dispersão, e o "modified z-score"
(fator 0,6745) como regra prática para sinalizar outliers — escolha
deliberada por ser menos sensível a caudas longas do que média/desvio
padrão clássicos, um problema documentado nos próprios dados de gasto
parlamentar (ver `reports/data_understanding.md`).

Para medir concentração de gasto em fornecedor único, usamos o **Índice de
Herfindahl-Hirschman (HHI)** [@hirschman1964paternity], originalmente uma
medida de concentração de mercado em economia industrial, aqui reaproveitada
para medir concentração de gasto por deputado.

Para avaliar a concordância entre a classificação do LLM e a rotulagem
humana, usamos o **coeficiente kappa de Cohen** [@cohen1960coefficient],
interpretado pela escala de referência de **Landis & Koch (1977)**
[@landis1977measurement] — na qual o kappa observado neste projeto (0,231,
ver `reports/evaluation_llm.md`) cai na faixa "razoável" (0,21–0,40), não
"substancial" (0,61–0,80).

A etapa de classificação por LLM segue a documentação oficial da API
Anthropic para saída estruturada via Pydantic [@anthropic_docs].

Este texto foi incorporado, sem alterações de conteúdo, à seção "Revisão da
Literatura" de `reports/paper/trabalho_final.qmd`.
