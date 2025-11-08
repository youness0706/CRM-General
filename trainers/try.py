import settings
from models import Payments
settings.configure()
for i in Payments.objects.all():
    print(i)