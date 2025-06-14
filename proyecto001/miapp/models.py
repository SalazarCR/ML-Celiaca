from django.db import models

# Create your models here.
from django.db import models

class Evaluacion(models.Model):
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)  # Campo correcto
    genero = models.CharField(max_length=1)
    resultado = models.CharField(max_length=10)
    probabilidad = models.FloatField()
    fecha = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.resultado}"
