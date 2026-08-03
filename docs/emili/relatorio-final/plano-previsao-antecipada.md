# Registro do piloto de previsão antecipada e plano de continuidade

**Bolsista:** Emili Vieira Tabuti

**Data da consolidação:** 30 de julho de 2026

**Situação:** piloto concluído; previsão antecipada não comprovada

## 1. Finalidade deste documento

Este documento registra a tentativa de transformar o protótipo de detecção contextual em um sistema de previsão antecipada.

Ele apresenta:

1. o que foi implementado;
2. quais dados foram analisados;
3. quais resultados foram obtidos;
4. por que a previsão não pôde ser comprovada;
5. como o resultado atual deve ser apresentado;
6. quais ações poderão viabilizar uma previsão futura.

Este arquivo não representa mais um plano ativo de treinamento prospectivo com a base atual.

## 2. Decisão científica

O resultado principal da Iniciação Científica será apresentado como **detecção contextual de ataques cibernéticos**.

O protótipo utiliza sequências recentes para reconhecer o estado observado no final da janela.

Esse procedimento não representa, por si só, a previsão de um ataque futuro.

A previsão antecipada será apresentada como:

- hipótese investigada;
- piloto metodológico;
- resultado negativo relevante;
- proposta de continuidade experimental.

Nenhum modelo prospectivo final será selecionado com os dados atuais.

O teste estrito permanecerá bloqueado para escolha de modelos, atributos ou limiares.

## 3. Pergunta investigada

O piloto avaliou a seguinte pergunta:

> Com base somente no tráfego disponível até o instante `t`, ocorrerá um ataque dentro de um horizonte futuro?

Foram considerados os horizontes:

- 5 segundos;
- 15 segundos;
- 30 segundos;
- 60 segundos.

Foram consideradas janelas históricas de:

- 30 segundos;
- 60 segundos;
- 120 segundos.

## 4. O que foi realizado

### 4.1 Auditoria temporal

Os campos `Stime` e `Ltime` do UNSW-NB15 foram auditados antes do escalonamento.

Os valores representam segundos Unix e não possuem durações negativas.

O arquivo original permaneceu inalterado durante todas as etapas.

### 4.2 Ordenação

Os fluxos foram ordenados por:

1. `source_file`;
2. `Stime`;
3. `Ltime`;
4. posição original para desempate.

As regressões temporais foram reduzidas de 250.850 para zero.

### 4.3 Identificação dos períodos de ataque

Um ataque foi considerado ativo quando algum fluxo malicioso cobria o instante `t`.

Foi utilizado o intervalo inclusivo:

```text
[Stime, Ltime]
```

Essa definição impediu que um ataque longo fosse dividido em falsos eventos.

### 4.4 Rótulos prospectivos

Um rótulo positivo exigiu:

1. ausência de ataque ativo em `t`;
2. início de ataque no intervalo `(t, t + H]`.

Foram produzidos:

- `Future_Attack_Label`;
- `Seconds_To_Attack`;
- `Next_Attack_Onset`;
- `Next_Attack_Event_ID`.

### 4.5 Atributos históricos

Os atributos utilizaram somente fluxos concluídos em:

```text
(t - W, t]
```

O campo `Ltime` determinou a disponibilidade operacional do fluxo.

Foram criados 60 atributos históricos.

Eles incluem:

- quantidade de fluxos;
- pacotes e bytes;
- estatísticas de duração;
- taxas temporais;
- endereços e portas distintos;
- entropias;
- proporções de protocolos e estados;
- crescimento e tendência.

Rótulos e metadados futuros não foram utilizados como atributos.

### 4.6 Conjunto estrito

O conjunto estrito removeu referências com ataques concluídos nos 120 segundos anteriores.

Esse filtro separou previsão do primeiro ataque recente e previsão de recorrência.

### 4.7 Divisão temporal

Foi aplicada uma purga de 180 segundos.

Esse valor corresponde a:

```text
120 segundos históricos + 60 segundos futuros
```

Não houve embaralhamento ou divisão estratificada aleatória.

Os eventos positivos foram mantidos em partições distintas.

## 5. Resultados do piloto

### 5.1 Estrutura temporal

| Verificação | Resultado |
|---|---:|
| Fluxos analisados | 1.584.259 |
| Arquivos de origem | 2 |
| Instantes temporais distintos | 66.484 |
| Instantes com início de fluxo malicioso | 26.226 |
| Instantes cobertos por ataque ativo | 28.625 |
| Instantes ativos sem novo início malicioso | 2.399 |
| Instantes com ataque e tráfego benigno simultâneo | 28.623 |
| Eventos observados após considerar a duração | 277 |

Quase todos os instantes ativos também contêm tráfego benigno.

Essa sobreposição dificulta a identificação de campanhas independentes.

### 5.2 Rótulos antes do filtro estrito

| Horizonte | Positivos | Negativos | Eventos cobertos |
|---:|---:|---:|---:|
| 5 s | 337 | 37.522 | 275 |
| 15 s | 390 | 37.469 | 276 |
| 30 s | 442 | 37.417 | 276 |
| 60 s | 466 | 37.393 | 277 |

A mediana da antecedência positiva foi um segundo em todos os horizontes.

Grande parte desses positivos ocorreu após ataques recentes.

### 5.3 Presença de ataques anteriores

Entre 85% e 97% dos positivos possuíam tráfego malicioso concluído na janela histórica.

Entre os negativos, essa participação permaneceu abaixo de 0,6%.

Portanto, a separação encontrada refletia principalmente:

- persistência de campanhas;
- recorrência de ataques;
- efeitos posteriores a ataques recentes.

Ela não demonstrava sinais anteriores ao primeiro ataque.

### 5.4 Resultado do filtro estrito

| Verificação | Resultado |
|---|---:|
| Instantes antes do filtro | 37.859 |
| Instantes estritos | 37.311 |
| Instantes removidos | 548 |
| Eventos positivos estritos | 5 |
| Linhas nos quatro horizontes | 149.244 |

Distribuição estrita:

| Horizonte | Positivos | Negativos |
|---:|---:|
| 5 s | 10 | 37.301 |
| 15 s | 24 | 37.287 |
| 30 s | 43 | 37.268 |
| 60 s | 46 | 37.265 |

### 5.5 Divisão por evento

Os cinco eventos estritos foram distribuídos da seguinte forma:

| Partição | Eventos |
|---|---:|
| Treino | 3 |
| Validação | 1 |
| Teste | 1 |

Distribuição das classes:

| Partição | Horizonte | Positivos | Negativos |
|---|---:|---:|---:|
| Treino | 5 s | 3 | 37.293 |
| Treino | 15 s | 12 | 37.284 |
| Treino | 30 s | 28 | 37.268 |
| Treino | 60 s | 31 | 37.265 |
| Validação | 5 s | 4 | 1 |
| Validação | 15 s | 4 | 1 |
| Validação | 30 s | 5 | 0 |
| Validação | 60 s | 5 | 0 |
| Teste | 5 s | 3 | 7 |
| Teste | 15 s | 8 | 2 |
| Teste | 30 s | 10 | 0 |
| Teste | 60 s | 10 | 0 |

Os horizontes de 30 e 60 segundos perderam a classe negativa nas partições futuras.

Os horizontes de 5 e 15 segundos mantiveram ambas as classes.

Entretanto, validação e teste possuem somente um evento positivo cada.

## 6. Por que a previsão não pôde ser comprovada

### 6.1 Poucos eventos independentes

O conjunto contém muitos fluxos, mas somente cinco eventos atendem ao protocolo estrito.

Quantidade de fluxos não substitui quantidade de campanhas independentes.

### 6.2 Validação e teste insuficientes

Um evento na validação e um no teste não sustentam estimativas confiáveis.

Uma única campanha pode alterar completamente as métricas.

### 6.3 Ausência de uma classe

Os horizontes de 30 e 60 segundos não possuem negativos na validação e no teste.

Assim, métricas binárias não podem ser interpretadas adequadamente.

### 6.4 Predominância de recorrência

A maioria dos sinais aparentemente fortes ocorre após ataques anteriores.

Um modelo poderia aprender que outro ataque ocorrerá durante a mesma campanha.

Esse resultado representa recorrência, não previsão estrita do primeiro ataque.

### 6.5 Ausência de identificador de campanha

O UNSW-NB15 possui rótulos por fluxo, mas não fornece campanhas independentes confiáveis.

Agrupar apenas por timestamp pode unir ataques diferentes ou dividir uma campanha longa.

### 6.6 Base adequada para outro objetivo

A base não está incorreta.

Ela é adequada para:

- detecção de ataques;
- classificação de tráfego;
- detecção contextual;
- análise de recorrência;
- testes metodológicos de prevenção de vazamento.

Ela é insuficiente para comprovar previsão antecipada estrita neste protocolo.

## 7. Conclusão científica do piloto

O piloto implementou um pipeline temporal auditável e sem acesso indevido ao futuro.

Essa implementação constitui uma contribuição metodológica da pesquisa.

Entretanto, os dados não sustentam treinamento, seleção e teste prospectivos confiáveis.

O resultado atual deverá ser descrito como:

> detecção contextual de ataques com base em sequências recentes de tráfego.

A tentativa prospectiva deverá ser descrita como:

> estudo de viabilidade que identificou limitações estruturais da base para previsão antecipada.

## 8. Como apresentar no relatório final

### 8.1 Formulação recomendada

> O protótipo realiza detecção contextual, pois classifica o estado associado ao final de uma sequência recente.

> Um piloto prospectivo foi implementado para avaliar a viabilidade de previsão antecipada.

> Após controle temporal e remoção de ataques recentes, permaneceram somente cinco eventos estritos.

> Essa quantidade foi insuficiente para avaliação confiável em validação e teste.

> A previsão antecipada permanece como continuidade experimental.

### 8.2 Afirmações que devem ser evitadas

Não utilizar:

- “o sistema prevê ataques”;
- “o modelo antecipa ataques”;
- “a solução foi validada para previsão”;
- “o modelo alerta antes do ataque”;
- “o UNSW-NB15 comprovou capacidade preditiva”.

Essas afirmações poderão aparecer somente como objetivos futuros.

### 8.3 Papel dos resultados prospectivos

Os resultados prospectivos deverão demonstrar:

- preocupação com validade temporal;
- identificação de vazamento;
- diferença entre detecção e previsão;
- análise crítica da base;
- justificativa dos trabalhos futuros.

Eles não deverão aparecer como comparação de desempenho com os modelos contextuais.

## 9. Próximos passos para conseguir previsão antecipada

### 9.1 Definir previamente a tarefa

Antes da nova coleta, será necessário definir:

- unidade de campanha;
- instante exato do início;
- janela histórica;
- horizontes futuros;
- intervalo de purga;
- critérios de utilidade;
- métricas principais;
- quantidade mínima de campanhas.

Essas decisões deverão ser registradas antes do treinamento.

### 9.2 Criar uma nova base controlada

Cada execução deverá conter:

```text
fase benigna
    → possível fase precursora
    → início registrado do ataque
    → ataque ativo
    → recuperação
```

Também deverão existir execuções completamente benignas.

Cada execução deverá possuir:

- identificador único;
- timestamps sincronizados;
- início e fim de cada fase;
- origem e destino;
- tipo de ataque;
- intensidade;
- duração;
- parâmetros utilizados;
- condição experimental;
- arquivos de captura preservados.

### 9.3 Aumentar a independência experimental

As campanhas deverão variar:

- horário;
- intensidade;
- duração;
- quantidade de origens;
- destino;
- padrão precursor;
- parâmetros de rede;
- condição benigna anterior.

Repetir o mesmo roteiro não cria campanhas verdadeiramente independentes.

### 9.4 Garantir partições utilizáveis

Treino, validação e teste deverão receber execuções completas e distintas.

Cada horizonte deverá possuir:

- exemplos positivos;
- exemplos negativos;
- múltiplos eventos na validação;
- múltiplos eventos no teste.

O tamanho mínimo deverá ser definido com o orientador antes da coleta.

O teste deverá permanecer fechado até a configuração final.

### 9.5 Reconstruir o pipeline prospectivo

A ordem obrigatória será:

1. preservar timestamps e identificadores;
2. separar campanhas completas;
3. aplicar a purga temporal;
4. criar rótulos dentro de cada partição;
5. construir atributos somente com o passado;
6. ajustar transformações somente no treino;
7. transformar validação e teste sem reajuste;
8. treinar o baseline;
9. selecionar configuração na validação;
10. avaliar uma única vez no teste.

### 9.6 Começar com baselines simples

A primeira avaliação deverá utilizar:

1. preditor de classe majoritária;
2. preditor baseado na taxa histórica;
3. regressão logística;
4. árvore de decisão;
5. Random Forest.

LSTM deverá ser considerada somente quando houver volume temporal suficiente.

### 9.7 Avaliar por evento

As métricas principais deverão incluir:

- PR-AUC;
- revocação de eventos;
- precisão de alertas;
- antecedência do primeiro alerta;
- antecedência mediana;
- falsos alertas por hora;
- eventos sem alerta;
- desempenho por horizonte;
- desempenho por tipo de ataque.

Métricas por registro deverão aparecer como complemento.

### 9.8 Separar detecção, recorrência e previsão

O futuro sistema deverá distinguir três tarefas:

| Tarefa | Pergunta |
|---|---|
| Detecção | Existe ataque agora? |
| Recorrência | Outro ataque ocorrerá durante uma campanha recente? |
| Previsão estrita | Um novo ataque começará após um período livre de ataques? |

Cada tarefa deverá possuir rótulos, métricas e modelos próprios.

### 9.9 Integrar somente após validação

A API não deverá chamar um resultado de “previsão” antes da validação prospectiva.

Um alerta preditivo futuro deverá informar:

- horizonte;
- probabilidade;
- antecedência estimada;
- versão do modelo;
- limiar;
- tipo de tarefa.

Alertas de detecção e previsão não deverão compartilhar a mesma interpretação.

## 10. Critérios para afirmar previsão antecipada

A previsão poderá ser afirmada somente quando:

1. o alvo representar um ataque futuro;
2. não existir ataque ativo em `t`;
3. a janela estrita não contiver ataque recente;
4. nenhum atributo utilizar dados posteriores a `t`;
5. treino, validação e teste tiverem campanhas distintas;
6. cada partição possuir positivos e negativos;
7. validação e teste contiverem múltiplos eventos;
8. transformações forem ajustadas somente no treino;
9. o modelo superar baselines simples;
10. a antecedência e os falsos alertas forem reportados.

Se algum critério falhar, o resultado deverá ser descrito como exploratório.

## 11. Próximas ações imediatas

### 11.1 Antes da entrega do relatório

- [ ] Revisar título, resumo, objetivos e conclusão.
- [ ] Classificar os modelos atuais como detecção contextual.
- [ ] Inserir o piloto como estudo de viabilidade.
- [ ] Apresentar os cinco eventos estritos.
- [ ] Explicar a ausência de classes nos horizontes maiores.
- [ ] Atualizar limitações e ameaças à validade.
- [ ] Atualizar o resumo estendido.
- [ ] Revisar textos da API e do painel.
- [ ] Validar a interpretação com o orientador.

### 11.2 Para a continuidade experimental

- [ ] Definir o protocolo de coleta.
- [ ] Definir a unidade de campanha.
- [ ] Definir o tamanho mínimo da amostra.
- [ ] Preparar execuções benignas de controle.
- [ ] Preparar fases precursoras observáveis.
- [ ] Registrar campanhas independentes.
- [ ] Congelar o protocolo antes do treinamento.
- [ ] Reexecutar o pipeline prospectivo.

## 12. Artefatos produzidos

| Artefato | Caminho |
|---|---|
| Auditoria temporal | `ml-pipeline/reports_local/prospective/unsw_temporal_audit.json` |
| Dataset ordenado | `ml-pipeline/data/processed/unsw_nb15_temporal_sorted.parquet` |
| Relatório da ordenação | `ml-pipeline/reports_local/prospective/unsw_temporal_sort.json` |
| Catálogo de eventos | `ml-pipeline/reports_local/prospective/unsw_attack_onsets.parquet` |
| Relatório de eventos | `ml-pipeline/reports_local/prospective/unsw_attack_onsets.json` |
| Rótulos prospectivos | `ml-pipeline/data/processed/unsw_nb15_prospective_labels.parquet` |
| Distribuição dos rótulos | `ml-pipeline/reports_local/prospective/unsw_prospective_labels.json` |
| Atributos históricos | `ml-pipeline/data/processed/unsw_nb15_historical_features.parquet` |
| Análise de precursores | `ml-pipeline/reports_local/prospective/unsw_precursor_analysis.json` |
| Divisão estrita | `ml-pipeline/data/processed/unsw_nb15_strict_temporal_split.parquet` |
| Relatório da divisão | `ml-pipeline/reports_local/prospective/unsw_strict_temporal_split.json` |

## 13. Informações que exigem decisão humana

- **TODO:** validar esta interpretação com o orientador.
- **TODO:** decidir se o CICIDS2017 original será recuperado.
- **TODO:** definir o cenário principal da nova coleta.
- **TODO:** definir a unidade operacional de campanha.
- **TODO:** definir a quantidade mínima de execuções.
- **TODO:** definir metas de antecedência e falsos alertas.
- **TODO:** confirmar recursos para novas capturas.
- **TODO:** decidir se a continuidade fará parte deste relatório ou de trabalho posterior.

## 14. Encerramento

A tentativa de previsão não foi descartada por falha de implementação.

Ela foi limitada pela estrutura experimental e pela quantidade de campanhas independentes.

O piloto mostrou que muitos sinais aparentes pertenciam a ataques recentes.

Após removê-los, restaram somente cinco eventos estritos.

Esse resultado justifica apresentar o sistema atual como detecção contextual.

Também justifica propor uma nova coleta como etapa necessária para previsão antecipada.
