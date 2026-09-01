from django.db import models

# Create your models here.

class Product(models.Model):
    name = models.CharField(max_length=30)
    stock = models.IntegerField()
    version = models.PositiveIntegerField(default=1)
    