from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_paciente, name='registro_paciente'),
    path('prediccion/', views.prediccion, name='prediccion'),
    path('finalizar/', views.finalizar, name='finalizar'),
    path('api/predict/', views.PrediccionAPIView.as_view(), name='api_prediccion'),
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('historial/', views.historial_evaluaciones, name='historial_evaluaciones'),
    path('estadisticas/', views.panel_estadisticas, name='panel_estadisticas'),
    path('usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('historial/', views.historial_evaluaciones, name='historial_evaluaciones'),
    path('exportar_excel/', views.exportar_excel, name='exportar_excel'),




]







