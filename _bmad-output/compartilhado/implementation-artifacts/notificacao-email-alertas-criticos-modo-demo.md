# Complemento: Notificacao por E-mail para Alertas Criticos do Modo Demo

> **Status: concluido** (2026-07-29) — Complementa a atividade do plano individual da Isabela sobre mecanismos de notificacao.

## Objetivo

Enviar notificacao por e-mail quando um evento critico for inserido no historico
do dashboard durante o modo demonstrativo, sem executar ataque real e sem expor
credenciais no repositorio.

## Implementacao

- `ml-pipeline/src/api/services/email_notifications.py`
  - Detecta alertas criticos com confianca maior ou igual a 90%.
  - Ignora trafego normal.
  - Envia e-mail via SMTP apenas quando `ALERT_EMAIL_ENABLED=true`.
  - Usa variaveis de ambiente para destinatario, remetente e credenciais SMTP.

- `ml-pipeline/src/api/routes/predict.py`
  - `POST /history/demo` registra o evento no historico e aciona a notificacao
    apenas para alertas criticos.

- `ml-pipeline/.env.example`
  - Documenta as variaveis de ambiente necessarias.

## Variaveis de ambiente

- `ALERT_EMAIL_ENABLED`
- `ALERT_EMAIL_TO`
- `ALERT_EMAIL_FROM`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`

## Validacao

- `.\.venv\Scripts\python.exe -m pytest tests\test_api_predict_mock.py`
- Resultado: 11 testes passaram.
