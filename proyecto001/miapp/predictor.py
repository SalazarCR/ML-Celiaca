import joblib
import os
from django.conf import settings

# Ruta absoluta al modelo dentro de la carpeta 'modelo_entrenado'
modelo_path = os.path.join(settings.BASE_DIR, 'miapp', 'modelo_entrenado', 'modelo_entrenado.pkl')

# Cargar el modelo
modelo = joblib.load(modelo_path)

def predecir_enfermedad(datos_entrada):
    resultado = modelo.predict([datos_entrada])
    probabilidades = modelo.predict_proba([datos_entrada])
    return resultado[0], probabilidades[0]
