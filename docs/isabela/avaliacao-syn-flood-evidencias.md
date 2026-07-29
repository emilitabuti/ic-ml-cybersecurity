# Avaliacao do cenario simulado de SYN flood

Este texto foi elaborado para complementar a parte individual do trabalho relacionada
ao ambiente simulado, ao monitoramento do dashboard e a avaliacao dos alertas
gerados. O cenario considerado utiliza apenas um tipo de ataque, o SYN flood, de
forma simulada e controlada. Nao ha execucao de ataque real contra uma rede ou
servico externo.

## Texto sugerido para o relatorio

Para avaliar o comportamento do sistema em um ambiente controlado, foi utilizado
um cenario simulado de SYN flood. Esse cenario foi escolhido por representar uma
forma conhecida de ataque de negacao de servico baseada no envio de multiplas
solicitacoes SYN sem a conclusao adequada do processo de estabelecimento de
conexao TCP. No projeto, entretanto, o ataque nao e executado de forma real. Em
vez disso, sao enviados eventos sinteticos para a API, permitindo observar se o
dashboard recebe, classifica e apresenta os alertas conforme o comportamento
esperado.

O fluxo de demonstracao foi estruturado a partir de cinco eventos: um registro de
trafego normal, um evento de SYN flood de baixa intensidade, um evento de SYN
flood de media intensidade e dois eventos de SYN flood de alta intensidade. Cada
registro possui os campos `prediction`, `confidence`, `model` e `timestamp`, que
sao consumidos pela interface web por meio do endpoint `GET /history`.

O tempo de resposta foi avaliado considerando o intervalo entre o envio de cada
evento simulado para a API e a confirmacao de que esse evento foi aceito pelo
endpoint de demonstracao. Na medicao realizada, os cinco eventos foram inseridos
com latencias de API de 8,86 ms, 4,86 ms, 4,74 ms, 4,41 ms e 3,82 ms. A media
observada foi de aproximadamente 5,34 ms. Esses valores indicam que, no ambiente
local de teste, a API recebeu e disponibilizou os eventos simulados rapidamente.

Na interface web, a exibicao dos eventos depende tambem do mecanismo de
atualizacao periodica do dashboard. A aplicacao consulta o endpoint `GET /history`
a cada 5 segundos. Portanto, depois que um evento e aceito pela API, o tempo para
ele aparecer visualmente no dashboard pode variar de acordo com o momento da
proxima consulta automatica, ficando limitado principalmente pelo intervalo de
polling configurado na aplicacao.

Durante a simulacao, o dashboard apresentou cinco janelas analisadas. Os tipos de
anomalia exibidos foram `Normal Traffic`, `SYN Flood - Low Intensity`,
`SYN Flood - Medium Intensity` e `SYN Flood - High Intensity`. A distribuicao de
severidade observada foi coerente com o comportamento esperado: os dois eventos
de alta intensidade foram classificados como criticos, os eventos de baixa e
media intensidade foram classificados como suspeitos e o trafego normal foi
classificado como seguro.

O monitoramento visual tambem indicou a origem dos eventos como a API FastAPI,
utilizando o endpoint `GET /history`. A secao de eventos recentes exibiu horario,
categoria, severidade, confianca e modelo utilizado. Alem disso, os campos de
correlacao, impacto potencial e acoes recomendadas apresentaram informacoes
contextuais relacionadas ao cenario de SYN flood, apoiando a interpretacao dos
alertas pelo usuario.

Apos a complementacao do dashboard, o sistema tambem passou a disponibilizar uma
secao de historico com filtros por status e tipo de ameaca. Nessa secao, cada
alerta pode receber feedback local do analista, sendo marcado como confirmado ou
falso positivo. Esse recurso apoia a analise da relevancia dos alertas gerados,
sem introduzir banco de dados proprio no frontend e mantendo o endpoint
`GET /history` como fonte principal dos eventos.

Tambem foi acrescentado um modo de demonstracao acionado pela propria interface
web. Esse modo reproduz a sequencia controlada de eventos do cenario SYN flood em
velocidades configuraveis, utilizando o endpoint `POST /history/demo`. Dessa
forma, a demonstracao do seminario pode ser feita sem trafego real e sem
preparacao manual adicional, preservando o carater seguro e controlado do
experimento.

Como complemento ao mecanismo de notificacao previsto no plano individual, o
backend tambem passou a suportar envio de e-mail para alertas criticos do modo
demo. O envio e opcional e depende de configuracao por variaveis de ambiente, de
modo que nenhuma credencial fica fixa no codigo. Quando habilitado, eventos
criticos com confianca maior ou igual a 90% geram uma mensagem para o e-mail
configurado.

Com base nos resultados obtidos, o comportamento observado foi compativel com as
expectativas definidas para a simulacao. Esperava-se que os registros de SYN flood
com maior confianca fossem destacados como eventos mais severos, enquanto o
registro de trafego normal deveria permanecer como seguro. Essa relacao foi
confirmada na visualizacao do dashboard, demonstrando que a integracao entre o
script de simulacao, a API e a interface web esta funcionando para o cenario
avaliado.

Ainda assim, e importante destacar que a avaliacao realizada possui carater
demonstrativo. O sistema, nesta etapa, valida o fluxo de geracao, envio,
classificacao visual e exibicao dos alertas simulados. A simulacao nao mede o
desempenho de um ataque real em rede, nem substitui uma avaliacao completa com
trafego real ou bases rotuladas de maior escala. Esses pontos podem ser
considerados como limitacoes do experimento e oportunidades para trabalhos
futuros.

## Evidencias tecnicas usadas

- Script de simulacao: `demos/syn-flood-dashboard-demo/run_syn_flood_demo.py`.
- Endpoint de insercao dos eventos de demonstracao: `POST /history/demo`.
- Endpoint consumido pelo dashboard: `GET /history`.
- Implementacao dos endpoints: `ml-pipeline/src/api/routes/predict.py`.
- Atualizacao automatica do dashboard: `dashboard/src/config.ts`, com
  `POLLING_INTERVAL_MS = 5000`.
- Regra de severidade: `dashboard/src/lib/severity.ts`.
- Tela principal do dashboard: `dashboard/src/App.tsx`.
- Historico com filtros e feedback: `dashboard/src/App.tsx`.
- Cliente dos endpoints de demonstracao: `dashboard/src/services/api.ts`.
- Notificacao por e-mail para alertas criticos:
  `ml-pipeline/src/api/services/email_notifications.py`.

## Medicao realizada

Medicao local realizada em 27/07/2026, com a API em `http://127.0.0.1:8000`.

| Evento | Confianca | Timestamp UTC | Latencia da API |
|---|---:|---|---:|
| Normal Traffic | 0,42 | 2026-07-27T20:58:37Z | 8,86 ms |
| SYN Flood - Low Intensity | 0,77 | 2026-07-27T20:58:38Z | 4,86 ms |
| SYN Flood - Medium Intensity | 0,86 | 2026-07-27T20:58:38Z | 4,74 ms |
| SYN Flood - High Intensity | 0,95 | 2026-07-27T20:58:38Z | 4,41 ms |
| SYN Flood - High Intensity | 0,97 | 2026-07-27T20:58:39Z | 3,82 ms |

Resultado da consulta posterior ao endpoint `GET /history`:

- Total de eventos retornados: 5.
- Evento mais recente: `SYN Flood - High Intensity`.
- Confianca do evento mais recente: 0,97.
- Timestamp do evento mais recente: `2026-07-27T20:58:39Z`.

## Comparacao entre esperado e observado

| Entrada simulada | Resultado esperado | Resultado observado |
|---|---|---|
| Normal Traffic, confianca 0,42 | Seguro | Seguro |
| SYN Flood - Low Intensity, confianca 0,77 | Suspeito | Suspeito |
| SYN Flood - Medium Intensity, confianca 0,86 | Suspeito | Suspeito |
| SYN Flood - High Intensity, confianca 0,95 | Critico | Critico |
| SYN Flood - High Intensity, confianca 0,97 | Critico | Critico |
