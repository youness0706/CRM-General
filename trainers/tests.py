from .models import School

School.objects.create(name="روض النجاح",
                       address="hay argana",
                       phone="1234567890",
                       email="info@rawd.com",
                       established_year=2024,
                       rent_amount=1000
                       ).save()
# Create your tests here.
