from django.db import models

# Create your models here.

class ShortURL(models.Model):
    original_url = models.URLField()
    short_code = models.CharField(unique=True)
    clicks = models.IntegerField(default=0)