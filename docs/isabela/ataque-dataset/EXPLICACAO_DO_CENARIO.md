# Explicacao detalhada do cenario simulado de SYN flood

## 1. Nome correto do experimento

O nome recomendado e:

**Cenario simulado de ataque DDoS/SYN flood com dados tabulares sinteticos.**

Ele nao deve ser chamado de ataque adversarial, porque nao ha, nesta etapa, uma
tentativa de enganar um modelo real treinado. O que existe e uma simulacao
controlada de trafego de rede e uma heuristica temporaria que representa a
classificacao que futuramente sera feita pelo modelo de Machine Learning.

## 2. Objetivo

O objetivo e avaliar se o sistema consegue representar, pontuar e exibir no
dashboard um caso de SYN flood em ambiente simulado.

Esse cenario foi escolhido porque faz sentido para deteccao de intrusao em rede:
um SYN flood tenta iniciar muitas conexoes em pouco tempo, gerando muitos pacotes
SYN e poucas respostas completas. Em dados tabulares, isso aparece como
desequilibrio entre requisicoes e respostas, alta taxa de pacotes e concentracao
em uma janela curta.

## 3. Por que usar varias amostras

Uma unica linha com confianca fixa seria insuficiente para avaliacao cientifica.
Por isso, o codigo gera varias execucoes do mesmo cenario:

- trafego normal;
- SYN flood de baixa intensidade;
- SYN flood de media intensidade;
- SYN flood de alta intensidade.

Com isso, ainda existe apenas um tipo principal de ataque estudado, mas ha dados
suficientes para comparar o comportamento esperado em diferentes intensidades.

## 4. Como o dataset sintetico e criado

O script `generate_syn_flood_dataset.py` cria o arquivo:

`sandbox_tabular_dataset/syn_flood_synthetic_samples.csv`

Cada linha representa uma janela de trafego de rede. As principais colunas sao:

- `flow_duration_ms`: duracao da janela analisada;
- `total_fwd_packets`: pacotes enviados;
- `total_bwd_packets`: pacotes de resposta;
- `flow_packets_s`: taxa de pacotes por segundo;
- `syn_flag_count`: quantidade de pacotes SYN;
- `ack_flag_count`: quantidade de pacotes ACK;
- `same_srv_rate`: concentracao no mesmo servico;
- `Binary_Label`: rotulo esperado, `0` para normal e `1` para ataque;
- `Attack_Type`: classe esperada do cenario.

O trafego normal recebe valores mais equilibrados. Os grupos de SYN flood recebem
valores progressivamente mais suspeitos.

## 5. Como a heuristica temporaria funciona

O script `evaluate_syn_flood_scenario.py` le o CSV e calcula sinais de anomalia.
Ele verifica:

1. Muitos SYN em relacao aos ACK.
2. Alta taxa de pacotes por segundo.
3. Rajada em janela curta.
4. Trafego concentrado no mesmo servico.
5. Muitos pacotes enviados para poucas respostas.

Cada sinal aumenta a confianca simulada. Essa confianca nao e resultado de um
modelo real de ML; ela e uma aproximacao temporaria para permitir que o dashboard
e as metricas sejam testados enquanto o pipeline real ainda nao existe.

## 6. Como a severidade e definida

A severidade segue a regra atual do dashboard:

- predicao normal: seguro;
- confianca maior ou igual a `0.90`: critico;
- confianca maior ou igual a `0.70`: suspeito;
- abaixo disso: seguro ou informativo, conforme o caso.

Assim, amostras de SYN flood de alta intensidade tendem a aparecer como
criticas, enquanto baixa intensidade pode aparecer como suspeita.

## 7. Como isso integra com o dashboard

O dashboard consome alertas pelo endpoint `GET /history`.

O script de avaliacao gera:

`results/dashboard_history_events.json`

Esse arquivo contem uma lista de eventos no mesmo contrato da API:

```json
{
  "prediction": "SYN Flood - High Intensity",
  "confidence": 0.95,
  "model": "isabela-syn-flood-heuristic-v1",
  "timestamp": "..."
}
```

No fluxo integrado atual, esse arquivo nao substitui o endpoint da API. Ele serve
como entrada do script `send_real_predictions_to_api.py`, que monta janelas no
schema do modelo carregado e chama o endpoint real `POST /predict`. As respostas
do modelo sao gravadas no historico em memoria da API e entao aparecem no
dashboard por `GET /history`.

Para exibir o cenario no dashboard, a API deve estar rodando normalmente:

```powershell
cd C:\Users\isagr\Documents\ic-ml-cybersecurity\ml-pipeline
uvicorn src.api.main:app --reload
```

Em outro terminal:

```powershell
cd C:\Users\isagr\Documents\ic-ml-cybersecurity
py .\docs\isabela\ataque-dataset\send_real_predictions_to_api.py --limit 20
```

## 8. Quais resultados sao coletados

O arquivo `results/evaluation_summary.json` registra:

- total de amostras;
- amostras corretamente identificadas;
- verdadeiros positivos;
- verdadeiros negativos;
- falsos positivos;
- falsos negativos;
- acuracia;
- tempo medio de resposta em milissegundos;
- confianca media por grupo;
- severidade exibida por grupo.

Esses dados atendem melhor ao plano individual porque permitem monitoramento,
coleta de metricas, comparacao com expectativas e base para o relatorio final.

## 9. Texto sugerido para o relatorio

Foi implementado um estudo de caso delimitado para deteccao de SYN flood em
ambiente simulado, utilizando dados tabulares sinteticos. O experimento gera
trafego normal e amostras de SYN flood em baixa, media e alta intensidade. Em
seguida, uma heuristica temporaria calcula a confianca da deteccao, produz
metricas quantitativas e exporta eventos compativeis com o endpoint de historico
utilizado pelo dashboard. Dessa forma, mesmo antes da integracao com o modelo
real de Machine Learning, e possivel avaliar o fluxo integrado de geracao,
classificacao simulada, exibicao de severidade e coleta de resultados.
