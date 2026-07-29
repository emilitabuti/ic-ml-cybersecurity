import logging
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

from src.api.schemas.prediction import PredictionResponse

logger = logging.getLogger(__name__)
load_dotenv()

ALERT_EMAIL_ENABLED_ENV = "ALERT_EMAIL_ENABLED"
ALERT_EMAIL_TO_ENV = "ALERT_EMAIL_TO"
ALERT_EMAIL_FROM_ENV = "ALERT_EMAIL_FROM"
SMTP_HOST_ENV = "SMTP_HOST"
SMTP_PORT_ENV = "SMTP_PORT"
SMTP_USERNAME_ENV = "SMTP_USERNAME"
SMTP_PASSWORD_ENV = "SMTP_PASSWORD"
SMTP_USE_TLS_ENV = "SMTP_USE_TLS"
CRITICAL_ALERT_THRESHOLD = 0.9


def is_critical_alert(prediction: PredictionResponse) -> bool:
    if "normal" in prediction.prediction.lower():
        return False

    return prediction.confidence >= CRITICAL_ALERT_THRESHOLD


def _is_email_enabled() -> bool:
    return os.getenv(ALERT_EMAIL_ENABLED_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_message(prediction: PredictionResponse, sender: str, recipient: str) -> EmailMessage:
    confidence = round(prediction.confidence * 100)
    message = EmailMessage()
    message["Subject"] = f"[Alerta de Seguranca] {prediction.prediction} - Severidade critica"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "Um evento de seguranca com severidade critica foi identificado pelo sistema de monitoramento.",
                "",
                "Resumo do alerta:",
                f"- Categoria: {prediction.prediction}",
                f"- Nivel de confianca: {confidence}%",
                f"- Origem da predicao: {prediction.model}",
                f"- Horario do evento: {prediction.timestamp}",
                "",
                "Interpretacao:",
                "O padrao observado apresenta indicadores compativeis com atividade anomala de rede e requer verificacao.",
                "",
                "Este alerta foi gerado automaticamente. Revise o contexto antes de tomar medidas corretivas.",
            ]
        )
    )
    return message


def send_critical_alert_email(prediction: PredictionResponse) -> bool:
    if not _is_email_enabled() or not is_critical_alert(prediction):
        return False

    recipient = os.getenv(ALERT_EMAIL_TO_ENV)
    sender = os.getenv(ALERT_EMAIL_FROM_ENV)
    smtp_host = os.getenv(SMTP_HOST_ENV)
    smtp_username = os.getenv(SMTP_USERNAME_ENV)
    smtp_password = os.getenv(SMTP_PASSWORD_ENV)
    smtp_port = int(os.getenv(SMTP_PORT_ENV, "587"))
    use_tls = os.getenv(SMTP_USE_TLS_ENV, "true").strip().lower() != "false"

    required = {
        ALERT_EMAIL_TO_ENV: recipient,
        ALERT_EMAIL_FROM_ENV: sender,
        SMTP_HOST_ENV: smtp_host,
        SMTP_USERNAME_ENV: smtp_username,
        SMTP_PASSWORD_ENV: smtp_password,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        logger.warning("Email de alerta nao enviado; variaveis ausentes: %s", ", ".join(missing))
        return False

    message = _build_message(prediction, sender=sender, recipient=recipient)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    except Exception:
        logger.exception("Falha ao enviar email de alerta critico.")
        return False

    logger.info("Email de alerta critico enviado para %s", recipient)
    return True
