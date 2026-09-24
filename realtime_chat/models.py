from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()
class Message(models.Model):
    sender = models.ForeignKey(User,on_delete=models.CASCADE)
    room = models.CharField(max_length=50)
    content = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

