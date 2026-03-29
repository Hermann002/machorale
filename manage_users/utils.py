from .tasks import send_code_to_user as send_code_to_user_task


def send_code_to_user(email, code):
    return send_code_to_user_task.delay(email, code)
