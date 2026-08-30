from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
import socket
import logging
import json
import smtplib
from django.template.exceptions import TemplateDoesNotExist

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_code_to_user(self, email: str, code: str):
    try:
        subject = "Code de vérification à usage unique"
        current_site = "ma chorale"

        # Rendu du template
        email_body = render_to_string(
            "emails/otp.html",
            {"otp": code, "user_email": email, "current_site": current_site},
        )

        # Construction de l'email
        d_email = EmailMessage(
            subject=subject,
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        d_email.content_subtype = "html"

        # Envoi
        d_email.send(fail_silently=False)

        logger.info(f"Email de vérification envoyé avec succès à {email}")
        return {"ok": True, "email": email}

    # ERREURS TRANSITOIRES (Réseau, Timeout)
    except (
        ConnectionRefusedError,
        socket.gaierror,
        socket.timeout,
        smtplib.SMTPServerDisconnected,
    ) as exc:
        logger.warning(
            f"Erreur réseau SMTP pour {email}. Nouvelle tentative dans 60s... "
            f"(Tentative {self.request.retries + 1}/{self.max_retries})"
        )
        # self.retry() lève automatiquement une exception Retry pour Celery
        raise self.retry(exc=exc)

    # ERREURS PERMANENTES (Config, Données)
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            f"Erreur d'authentification SMTP (vérifiez EMAIL_HOST_USER/PASSWORD). Échec définitif pour {email}."
        )
        raise exc  # Lève l'erreur pour que Celery marque la tâche comme FAILED

    except TemplateDoesNotExist as exc:
        logger.error(
            f"Le template 'emails/otp.html' est introuvable. Échec définitif pour {email}."
        )
        raise exc

    except Exception as exc:
        # ERREUR INATTENDUE (Catch-all)
        exc_info = (
            True  # est crucial : il affiche la trace complète (traceback) dans les logs
        )
        logger.error(
            f"Erreur inattendue lors de l'envoi à {email}: {str(exc)}", exc_info=True
        )
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_link_to_user(self, email, uuidb64, token):
    subject = "Password reset link for ma chorale"

    email_body = render_to_string(
        "emails/password_reset.html",
        {
            "user_email": email,
            "current_site": settings.SITE_URL,
            "uidb64": uuidb64,
            "token": token,
        },
    )

    from_email = settings.DEFAULT_FROM_EMAIL
    d_email = EmailMessage(
        subject=subject, body=email_body, from_email=from_email, to=[email]
    )
    d_email.content_subtype = "html"
    # SendGrid réécrit tous les <a href> avec ses URLs de tracking par défaut.
    # Pour un lien de réinitialisation, l'URL doit arriver intacte — on désactive
    # le click tracking uniquement pour cet email via le header SMTPAPI.
    d_email.extra_headers = {
        "X-SMTPAPI": json.dumps(
            {"filters": {"clicktrack": {"settings": {"enable": 0}}}}
        )
    }
    try:
        d_email.send(fail_silently=False)
    except (socket.gaierror, socket.timeout, OSError) as exc:
        logger.warning(
            f"Network error sending reset email to {email}: {exc}. Retrying..."
        )
        raise self.retry(exc=exc)
