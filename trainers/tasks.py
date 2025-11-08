from background_task import background
from trainers.views import send_payment_reminder

@background(schedule=0)  # Runs after 60 seconds
def send_payment_reminder_task():
    print("Background task running...")
    send_payment_reminder()
