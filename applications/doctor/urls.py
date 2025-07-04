from django.urls import path

from applications.doctor.views.atencion_medica import AtencionListView, AtencionCreateView, AtencionUpdateView, \
    AtencionDeleteView
from applications.doctor.views.cita_medica import (
    CitaMedicaListView, CitaMedicaCreateView, CitaMedicaUpdateView, CitaMedicaDeleteView,
    CalendarioCitasView, obtener_disponibilidad_calendario, obtener_horarios_disponibles
)
from applications.doctor.views.paypal_views import create_paypal_order, capture_paypal_payment
from applications.doctor.views.servicio import (
    ServicioListView, ServicioCreateView, ServicioUpdateView, ServicioDeleteView
)

app_name='doctor' # define un espacio de nombre para la aplicacion
urlpatterns = [
    # Rutas para vistas relacionadas con Atenciones Médicas
    path('atencion_list/', AtencionListView.as_view(), name="atencion_list"),
    path('atencion_create/', AtencionCreateView.as_view(), name="atencion_create"),
    path('atencion_update/<int:pk>/', AtencionUpdateView.as_view(), name="atencion_update"),
    path('atencion_delete/<int:pk>/', AtencionDeleteView.as_view(), name="atencion_delete"),
    
    # Rutas para vistas relacionadas con Citas Médicas
    path('cita_list/', CitaMedicaListView.as_view(), name="cita_list"),
    path('cita_create/', CitaMedicaCreateView.as_view(), name="cita_create"),
    path('cita_update/<int:pk>/', CitaMedicaUpdateView.as_view(), name="cita_update"),
    path('cita_delete/<int:pk>/', CitaMedicaDeleteView.as_view(), name="cita_delete"),
    
    # Rutas para calendario de citas
    path('calendario_citas/', CalendarioCitasView.as_view(), name="calendario_citas"),
    
    # APIs para calendario dinámico
    path('api/disponibilidad_calendario/', obtener_disponibilidad_calendario, name="api_disponibilidad_calendario"),
    path('api/horarios_disponibles/', obtener_horarios_disponibles, name="api_horarios_disponibles"),

    # Rutas para PayPal
    path('api/paypal/create-order/', create_paypal_order, name='create_paypal_order'),
    path('api/paypal/capture-payment/', capture_paypal_payment, name='capture_paypal_payment'),

    # Rutas para Servicios
    path('servicio_list/', ServicioListView.as_view(), name="servicio_list"),
    path('servicio_create/', ServicioCreateView.as_view(), name="servicio_create"),
    path('servicio_update/<int:pk>/', ServicioUpdateView.as_view(), name='servicio_update'),
    path('servicio_delete/<int:pk>/', ServicioDeleteView.as_view(), name='servicio_delete'),
]
