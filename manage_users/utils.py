from .tasks import send_link_to_user, send_code_to_user as send_code_to_user_task


def send_code_to_user(email, code):
    return send_code_to_user_task.delay(email, code)

def send_password_reset_link(email, uidb64, token):
    return send_link_to_user.delay(email, uidb64, token)