import json
from datetime import datetime, date, timedelta
from calendar import monthrange
from collections import defaultdict

from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from applications.security.components.mixin_crud import (
    CreateViewMixin, DeleteViewMixin, ListViewMixin, 
    PermissionMixin, UpdateViewMixin
)
from applications.doctor.models import CitaMedica, HorarioAtencion
from applications.core.models import Paciente


class CitaMedicaListView(PermissionMixin, ListViewMixin, ListView):
    template_name = 'doctor/citas/list.html'
    model = CitaMedica
    context_object_name = 'citas'
    permission_required = 'view_citamedica'
    paginate_by = 20

    def get_queryset(self):
        q1 = self.request.GET.get('q')
        if q1 is not None:
            self.query.add(Q(paciente__nombres__icontains=q1), Q.OR)
            self.query.add(Q(paciente__apellidos__icontains=q1), Q.OR)
            self.query.add(Q(observaciones__icontains=q1), Q.OR)
        return self.model.objects.filter(self.query).select_related('paciente').order_by('-fecha', '-hora_cita')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('doctor:cita_create')
        context['calendario_url'] = reverse_lazy('doctor:calendario_citas')
        return context


class CitaMedicaCreateView(PermissionMixin, CreateViewMixin, CreateView):
    model = CitaMedica
    template_name = 'doctor/citas/form.html'
    fields = ['paciente', 'fecha', 'hora_cita', 'estado', 'observaciones']
    success_url = reverse_lazy('doctor:cita_list')
    permission_required = 'add_citamedica'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grabar'] = 'Agendar Cita'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        cita = self.object
        messages.success(
            self.request, 
            f"Cita agendada exitosamente para {cita.paciente.nombre_completo} el {cita.fecha} a las {cita.hora_cita}"
        )
        return response


class CitaMedicaUpdateView(PermissionMixin, UpdateViewMixin, UpdateView):
    model = CitaMedica
    template_name = 'doctor/citas/form.html'
    fields = ['paciente', 'fecha', 'hora_cita', 'estado', 'observaciones']
    success_url = reverse_lazy('doctor:cita_list')
    permission_required = 'change_citamedica'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grabar'] = 'Actualizar Cita'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        cita = self.object
        messages.success(
            self.request, 
            f"Cita actualizada exitosamente para {cita.paciente.nombre_completo}"
        )
        return response


class CitaMedicaDeleteView(PermissionMixin, DeleteViewMixin, DeleteView):
    model = CitaMedica
    template_name = 'components/delete.html'
    success_url = reverse_lazy('doctor:cita_list')
    permission_required = 'delete_citamedica'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grabar'] = 'Cancelar Cita'
        context['description'] = f"¿Desea cancelar la cita de {self.object.paciente.nombre_completo} programada para el {self.object.fecha} a las {self.object.hora_cita}?"
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        paciente_nombre = self.object.paciente.nombre_completo
        fecha_cita = f"{self.object.fecha} {self.object.hora_cita}"
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f"Cita de {paciente_nombre} ({fecha_cita}) cancelada exitosamente."
        )
        return response


class CalendarioCitasView(PermissionMixin, ListView):
    template_name = 'doctor/citas/calendario.html'
    model = CitaMedica
    permission_required = 'view_citamedica'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año y mes actual o de parámetros
        hoy = date.today()
        anio = int(self.request.GET.get('anio', hoy.year))
        mes = int(self.request.GET.get('mes', hoy.month))
        
        context['anio_actual'] = anio
        context['mes_actual'] = mes
        context['fecha_actual'] = date(anio, mes, 1)
        
        # URLs para navegación
        context['create_url'] = reverse_lazy('doctor:cita_create')
        context['list_url'] = reverse_lazy('doctor:cita_list')
        
        return context


@login_required
@require_http_methods(["GET"])
def obtener_disponibilidad_calendario(request):
    """
    API endpoint para obtener la disponibilidad del calendario por año y mes
    """
    try:
        anio = int(request.GET.get('anio', date.today().year))
        mes = int(request.GET.get('mes', date.today().month))
        
        calendario = generar_calendario_disponibilidad(anio, mes)
        
        return JsonResponse({
            'success': True,
            'calendario': calendario,
            'anio': anio,
            'mes': mes
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener disponibilidad: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def obtener_horarios_disponibles(request):
    """
    API endpoint para obtener horarios disponibles de un día específico
    """
    try:
        fecha_str = request.GET.get('fecha')
        if not fecha_str:
            return JsonResponse({
                'success': False,
                'message': 'Fecha requerida'
            }, status=400)
        
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        horarios = generar_horarios_dia(fecha)
        
        return JsonResponse({
            'success': True,
            'horarios': horarios,
            'fecha': fecha_str
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener horarios: {str(e)}'
        }, status=500)


def generar_calendario_disponibilidad(anio, mes):
    """
    Genera un diccionario con la disponibilidad del calendario mensual
    """
    calendario = defaultdict(lambda: {
        'disponibles': 0,
        'ocupadas': 0,
        'atendidas': 0,
        'total': 0
    })
    
    dias_mes = monthrange(anio, mes)[1]
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, dias_mes)
    
    # Obtener todas las citas del mes
    citas = CitaMedica.objects.filter(
        fecha__range=(primer_dia, ultimo_dia)
    ).values('fecha', 'estado')
    
    # Contar citas por día y estado
    for cita in citas:
        fecha_str = cita['fecha'].strftime('%Y-%m-%d')
        estado = cita['estado']
        
        if estado == 'disponible':
            calendario[fecha_str]['disponibles'] += 1
        elif estado == 'ocupado':
            calendario[fecha_str]['ocupadas'] += 1
        elif estado == 'atendido':
            calendario[fecha_str]['atendidas'] += 1
        
        calendario[fecha_str]['total'] += 1
    
    # Obtener horarios de atención para calcular disponibilidad
    horarios = HorarioAtencion.objects.filter(activo=True)
    
    for dia in range(1, dias_mes + 1):
        fecha_actual = date(anio, mes, dia)
        fecha_str = fecha_actual.strftime('%Y-%m-%d')
        dia_semana = fecha_actual.strftime("%A").lower()
        
        # Mapear días en inglés a español
        dias_map = {
            'monday': 'lunes',
            'tuesday': 'martes', 
            'wednesday': 'miércoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sábado',
            'sunday': 'domingo'
        }
        
        dia_semana_es = dias_map.get(dia_semana, dia_semana)
        
        # Calcular slots disponibles para este día
        slots_disponibles = 0
        for horario in horarios:
            if horario.dia_semana.lower() == dia_semana_es:
                # Calcular número de slots de 30 minutos (duración típica de cita)
                inicio = datetime.combine(fecha_actual, horario.hora_inicio)
                fin = datetime.combine(fecha_actual, horario.hora_fin)
                
                # Restar tiempo de pausa si existe
                if horario.intervalo_desde and horario.intervalo_hasta:
                    pausa_inicio = datetime.combine(fecha_actual, horario.intervalo_desde)
                    pausa_fin = datetime.combine(fecha_actual, horario.intervalo_hasta)
                    tiempo_pausa = (pausa_fin - pausa_inicio).total_seconds() / 60
                else:
                    tiempo_pausa = 0
                
                tiempo_total = (fin - inicio).total_seconds() / 60 - tiempo_pausa
                slots_disponibles += int(tiempo_total / 30)  # 30 min por cita
        
        # Si no hay datos de citas para este día, inicializar
        if fecha_str not in calendario:
            calendario[fecha_str] = {
                'disponibles': slots_disponibles,
                'ocupadas': 0,
                'atendidas': 0,
                'total': slots_disponibles
            }
        else:
            # Ajustar disponibles basado en citas ocupadas/atendidas
            ocupadas_atendidas = calendario[fecha_str]['ocupadas'] + calendario[fecha_str]['atendidas']
            calendario[fecha_str]['disponibles'] = max(0, slots_disponibles - ocupadas_atendidas)
            calendario[fecha_str]['total'] = slots_disponibles
    
    return dict(calendario)


def generar_horarios_dia(fecha):
    """
    Genera los horarios disponibles para un día específico
    """
    dia_semana = fecha.strftime("%A").lower()
    
    # Mapear días en inglés a español
    dias_map = {
        'monday': 'lunes',
        'tuesday': 'martes', 
        'wednesday': 'miércoles',
        'thursday': 'jueves',
        'friday': 'viernes',
        'saturday': 'sábado',
        'sunday': 'domingo'
    }
    
    dia_semana_es = dias_map.get(dia_semana, dia_semana)
    
    # Obtener horarios de atención para este día
    horarios = HorarioAtencion.objects.filter(
        dia_semana__iexact=dia_semana_es,
        activo=True
    )
    
    # Obtener citas existentes para este día
    citas_existentes = CitaMedica.objects.filter(fecha=fecha).values_list('hora_cita', flat=True)
    
    horarios_disponibles = []
    
    for horario in horarios:
        hora_actual = horario.hora_inicio
        
        while hora_actual < horario.hora_fin:
            # Verificar si está en pausa
            if (horario.intervalo_desde and horario.intervalo_hasta and 
                horario.intervalo_desde <= hora_actual < horario.intervalo_hasta):
                # Saltar a después de la pausa
                hora_actual = horario.intervalo_hasta
                continue
            
            # Verificar si ya hay cita en este horario
            estado = 'disponible'
            if hora_actual in citas_existentes:
                cita = CitaMedica.objects.filter(fecha=fecha, hora_cita=hora_actual).first()
                estado = cita.estado if cita else 'ocupado'
            
            horarios_disponibles.append({
                'hora': hora_actual.strftime('%H:%M'),
                'estado': estado,
                'disponible': estado == 'disponible'
            })
            
            # Avanzar 30 minutos (duración típica de cita)
            dt = datetime.combine(fecha, hora_actual) + timedelta(minutes=30)
            hora_actual = dt.time()
    
    return horarios_disponibles
