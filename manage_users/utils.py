from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
# from ma_chorale.celery import app


# @app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_code_to_user(email, code):
    subject = "one time code password for email verification"

    current_site = "ma chorale"

    email_body = render_to_string('emails/otp.html', {
        'otp': code,
        'user_email': email,
        'current_site': current_site
    })

    from_email = settings.EMAIL_HOST_USER

    d_email = EmailMessage(
        subject=subject,
        body=email_body,
        from_email=from_email,
        to=[email]
    )
    d_email.content_subtype = "html"

    d_email.send(fail_silently=False)

    return {"ok": True}