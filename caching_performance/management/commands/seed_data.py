 
from faker import Faker
from ...models import ShortURL
import random,string
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):

        fake = Faker()
       
        for _ in range(100000):
            original_url = fake.url()
            short_code = ''.join(
                random.choices(string.ascii_letters + string.digits, k=6)
            )
            ShortURL.objects.create(original_url=original_url,short_code=short_code)

        self.stdout.write(self.style.SUCCESS("100,000 records created successfully."))
