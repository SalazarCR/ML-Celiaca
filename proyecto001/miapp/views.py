import matplotlib.pyplot as plt
import base64

from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from xhtml2pdf import pisa
from io import BytesIO
import numpy as np
import joblib
import json
import os
import csv
from datetime import datetime
from io import BytesIO as IO
from .models import Evaluacion
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

modelo_path = os.path.join(settings.BASE_DIR, 'miapp', 'modelo_entrenado', 'modelo_entrenado.pkl')
modelo = joblib.load(modelo_path)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.groups.filter(name='Administrador').exists():
                return redirect('panel_admin')
            elif user.groups.filter(name='PersonalMedico').exists():
                return redirect('registro_paciente')
            else:
                return render(request, 'login.html', {'error': 'No tienes permisos asignados'})
        else:
            return render(request, 'login.html', {'error': 'Credenciales inválidas'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def es_administrador(user):
    return user.groups.filter(name='Administrador').exists()

def es_medico(user):
    return user.groups.filter(name='PersonalMedico').exists()

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Administrador', 'PersonalMedico']).exists())
def registro_paciente(request):
    if request.method == 'POST':
        request.session['nombre'] = request.POST.get('nombre')
        request.session['apellido_paterno'] = request.POST.get('apellido_paterno')
        request.session['apellido_materno'] = request.POST.get('apellido_materno')
        request.session['correo'] = request.POST.get('correo')
        request.session['genero'] = request.POST.get('genero')
        return redirect('prediccion')
    return render(request, 'registro.html')

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Administrador', 'PersonalMedico']).exists())
def prediccion(request):
    if request.method == 'POST':
        datos = [
            int(request.POST.get('edad')),
            int(request.POST.get('genero')),
            int(request.POST.get('diabetes')),
            int(request.POST.get('tipo_diabetes')),
            int(request.POST.get('diarrea')),
            int(request.POST.get('baja_estatura')),
            int(request.POST.get('perdida_peso')),
            int(request.POST.get('heces_pastosas')),
            float(request.POST.get('iga')),
            float(request.POST.get('igg')),
            float(request.POST.get('igm'))
        ]

        resultado = modelo.predict([datos])[0]
        probabilidad = modelo.predict_proba([datos])[0]

        evaluacion = Evaluacion.objects.create(
            nombre=request.session['nombre'],
            apellidos=request.session['apellido_paterno'] + ' ' + request.session['apellido_materno'],
            resultado='Positivo' if resultado == 1 else 'Negativo',
            probabilidad=round(max(probabilidad) * 100, 2),
            genero = int(request.POST.get('genero', 0))
        )

        request.session['resultado'] = int(resultado)
        request.session['probabilidad'] = round(max(probabilidad) * 100, 2)

        return render(request, 'resultado_pdf.html', {
            'nombre': evaluacion.nombre,
            'apellido': evaluacion.apellidos,
            'resultado': resultado,
            'probabilidad': evaluacion.probabilidad,
            'mostrar_finalizar': True,
            'mostrar_botones_extra': True
        })
    return render(request, 'prediccion.html', {'mostrar_botones_extra': True})

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['Administrador', 'PersonalMedico']).exists())
def finalizar(request):
    context = {
        'nombre': request.session.get('nombre'),
        'apellido': request.session.get('apellido_paterno') + ' ' + request.session.get('apellido_materno'),
        'resultado': request.session.get('resultado'),
        'probabilidad': request.session.get('probabilidad'),
        'mostrar_finalizar': False,
        'mostrar_botones_extra': True
    }

    html = render_to_string('resultado_pdf.html', context)
    response = BytesIO()
    pisa.CreatePDF(html, dest=response)

    correo = EmailMessage(
        subject='Resultado de Predicción - Enfermedad Celíaca',
        body='Adjunto encontrará el resultado de su análisis y recomendaciones.',
        from_email='medico.hospital2000@gmail.com',
        to=[request.session.get('correo')]
    )
    correo.attach('resultado.pdf', response.getvalue(), 'application/pdf')
    correo.send()

    return redirect('registro_paciente')

@login_required
@user_passes_test(es_administrador)
def panel_admin(request):
    return render(request, 'panel_admin.html')

@login_required
@user_passes_test(es_administrador)
def historial_evaluaciones(request):
    filtro_nombre = request.GET.get('nombre', '')
    filtro_resultado = request.GET.get('resultado', '')

    historial = Evaluacion.objects.all()
    if filtro_nombre:
        historial = historial.filter(nombre__icontains=filtro_nombre)
    if filtro_resultado and filtro_resultado != "Todos":
        historial = historial.filter(resultado__icontains=filtro_resultado)

    return render(request, 'historial.html', {
        'historial': historial,
        'filtro_nombre': filtro_nombre,
        'filtro_resultado': filtro_resultado
    })

@login_required
@user_passes_test(es_administrador)
def exportar_excel(request):
    historial = Evaluacion.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="historial_evaluaciones.csv"'

    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Nombre', 'Apellidos', 'Resultado', 'Probabilidad'])
    for row in historial:
        writer.writerow([row.fecha, row.nombre, row.apellidos, row.resultado, row.probabilidad])

    return response

@login_required
@user_passes_test(es_administrador)
def panel_estadisticas(request):
    historial = Evaluacion.objects.all()

    positivos = historial.filter(resultado='Positivo').count()
    negativos = historial.filter(resultado='Negativo').count()
    hombres = historial.filter(genero=0).count()
    mujeres = historial.filter(genero=1).count()

    fechas = [e.fecha.strftime('%Y-%m-%d') for e in historial]
    conteo_fechas = {}
    for f in fechas:
        conteo_fechas[f] = conteo_fechas.get(f, 0) + 1

    if (positivos + negativos) == 0:
        positivos = negativos = 1

    if (hombres + mujeres) == 0:
        hombres = mujeres = 1

    fig1 = plt.figure()
    plt.pie([positivos, negativos], labels=['Positivos', 'Negativos'], autopct='%1.1f%%')
    buffer1 = BytesIO()
    plt.savefig(buffer1, format='png')
    buffer1.seek(0)
    img_base64_1 = base64.b64encode(buffer1.read()).decode()
    plt.close(fig1)

    fig2 = plt.figure()
    plt.pie([hombres, mujeres], labels=['Hombres', 'Mujeres'], autopct='%1.1f%%')
    buffer2 = BytesIO()
    plt.savefig(buffer2, format='png')
    buffer2.seek(0)
    img_base64_2 = base64.b64encode(buffer2.read()).decode()
    plt.close(fig2)

    fig3 = plt.figure()
    fechas_ordenadas = sorted(conteo_fechas)
    plt.bar(fechas_ordenadas, [conteo_fechas[f] for f in fechas_ordenadas])
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer3 = BytesIO()
    plt.savefig(buffer3, format='png')
    buffer3.seek(0)
    img_base64_3 = base64.b64encode(buffer3.read()).decode()
    plt.close(fig3)

    return render(request, 'panel_estadisticas.html', {
        'grafico_diagnostico': img_base64_1,
        'grafico_genero': img_base64_2,
        'grafico_fechas': img_base64_3,
    })

@login_required
@user_passes_test(es_administrador)
def gestion_usuarios(request):
    if request.method == 'POST':
        if 'crear' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            email = request.POST.get('email')
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, password=password, email=email)
                grupo = Group.objects.get(name='PersonalMedico')
                user.groups.add(grupo)
        elif 'eliminar' in request.POST:
            user_id = request.POST.get('user_id')
            User.objects.filter(id=user_id).delete()
        elif 'editar' in request.POST:
            user_id = request.POST.get('user_id')
            username = request.POST.get('username')
            email = request.POST.get('email')
            user = User.objects.get(id=user_id)
            user.username = username
            user.email = email
            user.save()

    medicos = User.objects.filter(groups__name='PersonalMedico')
    return render(request, 'gestion_usuarios.html', {'medicos': medicos})

class PrediccionAPIView(APIView):
    def get(self, request):
        return Response({"mensaje": "API activa. Use método POST para enviar datos."})

    def post(self, request):
        try:
            data = request.data
            datos = [
                int(data['edad']),
                int(data['genero']),
                int(data['diabetes']),
                int(data['tipo_diabetes']),
                int(data['diarrea']),
                int(data['baja_estatura']),
                int(data['perdida_peso']),
                int(data['heces_pastosas']),
                float(data['iga']),
                float(data['igg']),
                float(data['igm'])
            ]
            resultado = modelo.predict([datos])[0]
            probabilidad = modelo.predict_proba([datos])[0]

            return Response({
                'resultado': 'Positivo' if resultado == 1 else 'Negativo',
                'probabilidad': round(max(probabilidad) * 100, 2)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)







