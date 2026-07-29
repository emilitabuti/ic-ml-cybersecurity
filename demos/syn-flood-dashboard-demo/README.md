# Demo de SYN flood para o dashboard

Este diretorio contem uma demonstracao simples fora da pasta individual da
Isabela. Ela nao executa ataque real: apenas envia eventos simulados para a API,
que passam a aparecer no dashboard pelo endpoint `GET /history`.

## Como usar

Em um terminal, suba a API:

```powershell
cd C:\Users\isagr\Documents\ic-ml-cybersecurity\ml-pipeline
uvicorn src.api.main:app --reload
```

Em outro terminal, suba o dashboard normalmente.

Depois, na raiz do repositorio, execute:

```powershell
py .\demos\syn-flood-dashboard-demo\run_syn_flood_demo.py
```

O script limpa o historico de demo e envia uma sequencia curta:

- trafego normal;
- SYN flood de baixa intensidade;
- SYN flood de media intensidade;
- SYN flood de alta intensidade;
- novo alerta de alta intensidade.

Para enviar todos os eventos de uma vez:

```powershell
py .\demos\syn-flood-dashboard-demo\run_syn_flood_demo.py --delay 0
```

Para preservar alertas de uma execucao anterior:

```powershell
py .\demos\syn-flood-dashboard-demo\run_syn_flood_demo.py --no-clear
```

Observacao: se a API estiver usando a variavel
`ISABELA_SYN_FLOOD_HISTORY_FILE`, o endpoint `GET /history` continuara
priorizando o arquivo configurado por essa variavel.
