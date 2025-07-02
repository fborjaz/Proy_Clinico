import json
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone

from applications.core.models import Paciente, Medicamento, Diagnostico
from applications.doctor.forms.atencion import AtencionForm
from applications.doctor.models import Atencion, DetalleAtencion
from applications.security.components.mixin_crud import CreateViewMixin, DeleteViewMixin, ListViewMixin, \
    PermissionMixin, UpdateViewMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q

from proy_clinico.util import save_audit


class AtencionListView(PermissionMixin, ListViewMixin, ListView):
    template_name = 'doctor/atenciones/list.html'
    model = Atencion
    context_object_name = 'atenciones'
    permission_required = 'view_atencion'

    def get_queryset(self):
        q1 = self.request.GET.get('q')

        if q1  is not None:
               self.query.add(Q(paciente__nombres__icontains=q1), Q.OR)
               self.query.add(Q(paciente__apellidos__icontains=q1), Q.OR)
               self.query.add(Q(motivo_consulta__icontains=q1), Q.OR)
        return self.model.objects.filter(self.query).order_by('-fecha_atencion')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('doctor:atencion_create')

        return context


class AtencionCreateView(PermissionMixin, CreateViewMixin, CreateView):
    model = Atencion
    template_name = 'doctor/atenciones/form.html'
    form_class = AtencionForm
    success_url = reverse_lazy('doctor:atencion_list')
    permission_required = 'add_atencion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Grabar Atención'
        context['back_url'] = self.success_url
        context['diagnosticos']= Diagnostico.objects.filter(activo=True)
        context['medicamentos'] = (Medicamento.objects.filter(activo=True)
            .select_related('tipo', 'marca_medicamento')
            .only('id', 'nombre', 'concentracion', 'via_administracion',
                  'precio', 'cantidad', 'tipo__nombre', 'marca_medicamento__nombre'
                  ).order_by('nombre'))

        context['paciente_json'] = 'null'
        context['medicamentos_json'] = '[]'  # Array vacío
        context['modo_edicion'] = False
        return context


    def post(self, request, *args, **kwargs):
        # Convertir el cuerpo de la solicitud a un diccionario Python
        data = json.loads(request.body)

        # Extraer los objetos anidados
        signos_vitales = data.get('signosVitales', {})
        evaluacion_clinica = data.get('evaluacionClinica', {})
        plan_terapeutico = data.get('planTerapeutico', {})
        medicamentos = data.get('medicamentos', [])

        # Conversiones simples (el frontend ya validó)
        def to_int(value):
            return int(value) if value is not None and value != '' else None

        def to_decimal(value):
            return Decimal(str(value)) if value is not None and value != '' else None

        try:
            with transaction.atomic():
                # Crear la instancia del modelo Atencion
                atencion = Atencion.objects.create(
                    # Datos básicos
                    paciente_id=to_int(data.get('paciente')),

                    # Signos vitales
                    presion_arterial=signos_vitales.get('presionArterial'),
                    pulso=to_int(signos_vitales.get('pulso')),
                    temperatura=to_decimal(signos_vitales.get('temperatura')),
                    frecuencia_respiratoria=to_int(signos_vitales.get('frecuenciaRespiratoria')),
                    saturacion_oxigeno=to_decimal(signos_vitales.get('saturacionOxigeno')),
                    peso=to_decimal(signos_vitales.get('peso')),
                    altura=to_decimal(signos_vitales.get('altura')),
                    es_control=bool(signos_vitales.get('consultaControl', False)),

                    # Evaluación clínica
                    motivo_consulta=evaluacion_clinica.get('motivoConsulta', ''),
                    sintomas=evaluacion_clinica.get('sintomas', ''),
                    examen_fisico=evaluacion_clinica.get('examenFisico'),

                    # Plan terapéutico
                    tratamiento=plan_terapeutico.get('tratamiento', ''),
                    examenes_enviados=plan_terapeutico.get('examenesEnviados'),
                    comentario_adicional=plan_terapeutico.get('comentarioAdicional'),

                    # Fecha automática
                    fecha_atencion=timezone.now()
                )

                # Procesar diagnósticos
                diagnostico_ids = evaluacion_clinica.get('diagnostico', [])
                if diagnostico_ids:
                    diagnosticos = Diagnostico.objects.filter(id__in=diagnostico_ids)
                    atencion.diagnostico.set(diagnosticos)

                # Procesar medicamentos
                for medicamento in medicamentos:
                    DetalleAtencion.objects.create(
                        atencion=atencion,
                        medicamento_id=to_int(medicamento.get('id')),
                        cantidad=to_int(medicamento.get('cantidad')),
                        prescripcion=medicamento.get('prescripcion'),
                        duracion_tratamiento=to_int(medicamento.get('duracion')),
                        frecuencia_diaria=to_int(medicamento.get('frecuencia'))
                    )

                # Guardar auditoría
                save_audit(request, atencion, "ADICION")

                # Mensaje de éxito
                messages.success(request, f"Éxito al registrar la atención médica #{atencion.id}")

                # Respuesta exitosa
                return JsonResponse({
                    "msg": "Atención médica registrada exitosamente",
                    "id": atencion.id,
                    "fecha": atencion.fecha_atencion.strftime('%Y-%m-%d %H:%M:%S'),
                    "paciente": str(atencion.paciente)
                }, status=200)

        except Exception as e:
            messages.error(request, f"Error al registrar la atención médica")
            return JsonResponse({
                "msg": f"Error al registrar la atención médica: {str(e)}"
            }, status=500)


class AtencionUpdateView(PermissionMixin, UpdateViewMixin, UpdateView):
    model = Atencion
    template_name = 'doctor/atenciones/form.html'
    form_class = AtencionForm
    success_url = reverse_lazy('doctor:atencion_list')
    permission_required = 'change_atencion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grabar'] = 'Actualizar Atención'
        context['back_url'] = self.success_url

        # Contextos iguales al CreateView
        context['diagnosticos'] = Diagnostico.objects.filter(activo=True)
        context['medicamentos'] = (Medicamento.objects.filter(activo=True)
                                   .select_related('tipo', 'marca_medicamento')
                                   .only('id', 'nombre', 'concentracion', 'via_administracion',
                                         'precio', 'cantidad', 'tipo__nombre', 'marca_medicamento__nombre'
                                         ).order_by('nombre'))

        # Contexto específico para el update: detalles de atención actual
        atencion = self.get_object()

        # Obtener contexto completo del paciente para edición
        contexto_paciente = obtener_contexto_paciente(atencion.paciente.id)
        context['paciente_json'] = contexto_paciente['paciente_json']
        context['paciente_data'] = contexto_paciente['paciente_data']
        context['modo_edicion'] = True

        # Datos de la atención actual para usar directamente en el HTML
        context['atencion'] = atencion
        print("atenciones")
        print(atencion.temperatura)
        print(type(atencion.temperatura))
        # Solo los medicamentos para cargar dinámicamente con JavaScript
        medicamentos = []
        for detalle in atencion.detalles.select_related('medicamento').all():
            medicamento_dict = {
                'id': detalle.medicamento.id,
                'nombre': detalle.medicamento.nombre,
                'concentracion': detalle.medicamento.concentracion,
                'via_administracion': detalle.medicamento.via_administracion,
                'cantidad': detalle.cantidad,
                'prescripcion': detalle.prescripcion,
                'duracion': detalle.duracion_tratamiento,
                'frecuencia': detalle.frecuencia_diaria,
                'precio': float(detalle.medicamento.precio) if detalle.medicamento.precio else 0
            }
            medicamentos.append(medicamento_dict)

        # Solo los medicamentos en JSON para JavaScript
        context['medicamentos_json'] = json.dumps(medicamentos)

        return context

    def post(self, request, *args, **kwargs):
        # Obtener la instancia actual que se va a actualizar
        atencion = self.get_object()

        # Convertir el cuerpo de la solicitud a un diccionario Python
        data = json.loads(request.body)

        # Extraer los objetos anidados
        signos_vitales = data.get('signosVitales', {})
        evaluacion_clinica = data.get('evaluacionClinica', {})
        plan_terapeutico = data.get('planTerapeutico', {})
        medicamentos = data.get('medicamentos', [])

        # Conversiones simples (el frontend ya validó)
        def to_int(value):
            return int(value) if value is not None and value != '' else None

        def to_decimal(value):
            return Decimal(str(value)) if value is not None and value != '' else None

        try:
            with transaction.atomic():
                # Actualizar la instancia existente de Atencion
                atencion.paciente_id = to_int(data.get('paciente'))

                # Signos vitales
                atencion.presion_arterial = signos_vitales.get('presionArterial')
                atencion.pulso = to_int(signos_vitales.get('pulso'))
                atencion.temperatura = to_decimal(signos_vitales.get('temperatura'))
                atencion.frecuencia_respiratoria = to_int(signos_vitales.get('frecuenciaRespiratoria'))
                atencion.saturacion_oxigeno = to_decimal(signos_vitales.get('saturacionOxigeno'))
                atencion.peso = to_decimal(signos_vitales.get('peso'))
                atencion.altura = to_decimal(signos_vitales.get('altura'))
                atencion.es_control = bool(signos_vitales.get('consultaControl', False))

                # Evaluación clínica
                atencion.motivo_consulta = evaluacion_clinica.get('motivoConsulta', '')
                atencion.sintomas = evaluacion_clinica.get('sintomas', '')
                atencion.examen_fisico = evaluacion_clinica.get('examenFisico')

                # Plan terapéutico
                atencion.tratamiento = plan_terapeutico.get('tratamiento', '')
                atencion.examenes_enviados = plan_terapeutico.get('examenesEnviados')
                atencion.comentario_adicional = plan_terapeutico.get('comentarioAdicional')

                # Guardar los cambios en la atención
                atencion.save()

                # Procesar diagnósticos
                diagnostico_ids = evaluacion_clinica.get('diagnostico', [])
                if diagnostico_ids:
                    diagnosticos = Diagnostico.objects.filter(id__in=diagnostico_ids)
                    atencion.diagnostico.set(diagnosticos)
                else:
                    # Si no hay diagnósticos, limpiar la relación
                    atencion.diagnostico.clear()

                # Procesar medicamentos: borrar existentes y crear nuevos
                DetalleAtencion.objects.filter(atencion=atencion).delete()

                for medicamento in medicamentos:
                    DetalleAtencion.objects.create(
                        atencion=atencion,
                        medicamento_id=to_int(medicamento.get('id')),
                        cantidad=to_int(medicamento.get('cantidad')),
                        prescripcion=medicamento.get('prescripcion'),
                        duracion_tratamiento=to_int(medicamento.get('duracion')),
                        frecuencia_diaria=to_int(medicamento.get('frecuencia'))
                    )

                # Guardar auditoría para modificación
                save_audit(request, atencion, "MODIFICACION")

                # Mensaje de éxito
                messages.success(request, f"Éxito al actualizar la atención médica #{atencion.id}")

                # Respuesta exitosa
                return JsonResponse({
                    "msg": "Atención médica actualizada exitosamente",
                    "id": atencion.id,
                    "fecha": atencion.fecha_atencion.strftime('%Y-%m-%d %H:%M:%S'),
                    "paciente": str(atencion.paciente)
                }, status=200)

        except Exception as e:
            messages.error(request, f"Error al actualizar la atención médica")
            return JsonResponse({
                "msg": f"Error al actualizar la atención médica: {str(e)}"
            }, status=500)

class AtencionDeleteView(PermissionMixin, DeleteViewMixin, DeleteView):
    model = Atencion
    template_name = 'core/delete.html'
    success_url = reverse_lazy('doctor:atencion_list')
    permission_required = 'delete_atencion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Eliminar Atención'
        context['description'] = f"¿Desea eliminar la atención de: {self.object.paciente}?"
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        paciente_nombre = self.object.paciente
        response = super().form_valid(form)
        messages.success(self.request, f"Éxito al eliminar lógicamente la atención de {paciente_nombre}.")
        return response


def obtener_contexto_paciente(id_paciente):
    try:
        paciente = Paciente.objects.select_related('tipo_sangre').prefetch_related(
            'atenciones__diagnostico',
            'atenciones__detalles__medicamento'
        ).get(id=id_paciente, activo=True)

        edad = paciente.edad
        # Obtener atenciones anteriores (últimas 10)
        atenciones = []
        for atencion in paciente.atenciones.all()[:10]:
            # Obtener prescripciones/detalles de esta atención
            detalles = []
            for detalle in atencion.detalles.all():
                detalle_dict = {
                    'medicamento': detalle.medicamento.nombre if detalle.medicamento else '',
                    'cantidad': detalle.cantidad,
                    'prescripcion': detalle.prescripcion,
                    'duracion_tratamiento': detalle.duracion_tratamiento,
                    'frecuencia_diaria': detalle.frecuencia_diaria,
                }
                detalles.append(detalle_dict)

            # Obtener diagnósticos
            diagnosticos = [d.descripcion for d in atencion.diagnostico.all()]

            # Determinar tipo de consulta
            tipo_consulta = "Chequeo"
            if atencion.es_control:
                tipo_consulta = "Control"
            elif "urgencia" in atencion.motivo_consulta.lower() or "dolor" in atencion.motivo_consulta.lower():
                tipo_consulta = "Urgencia"

            atencion_dict = {
                'id': atencion.id,
                'fecha_atencion': atencion.fecha_atencion.isoformat(),
                'tipo_consulta': tipo_consulta,

                # Signos vitales
                'presion_arterial': atencion.presion_arterial,
                'pulso': atencion.pulso,
                'temperatura': float(atencion.temperatura) if atencion.temperatura else '',
                'frecuencia_respiratoria': atencion.frecuencia_respiratoria,
                'saturacion_oxigeno': float(atencion.saturacion_oxigeno) if atencion.saturacion_oxigeno else '',
                'peso': float(atencion.peso) if atencion.peso else '',
                'altura': float(atencion.altura) if atencion.altura else '',
                'imc': atencion.calcular_imc,

                # Contenido de la atención
                'motivo_consulta': atencion.motivo_consulta,
                'sintomas': atencion.sintomas,
                'tratamiento': atencion.tratamiento,
                'diagnosticos': diagnosticos,
                'examen_fisico': atencion.examen_fisico,
                'examenes_enviados': atencion.examenes_enviados,
                'comentario_adicional': atencion.comentario_adicional,
                'es_control': atencion.es_control,

                # Prescripciones
                'prescripciones': detalles
            }
            atenciones.append(atencion_dict)

        # Crear diccionario del paciente
        paciente_data = {
            'id': paciente.id,
            'nombres': paciente.nombres,
            'apellidos': paciente.apellidos,
            'cedula_ecuatoriana': paciente.cedula_ecuatoriana,
            'dni': paciente.dni,
            'fecha_nacimiento': paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else '',
            'edad': edad,
            'telefono': paciente.telefono,
            'email': paciente.email,
            'sexo': paciente.sexo,
            'estado_civil': paciente.estado_civil,
            'direccion': paciente.direccion,
            'latitud': float(paciente.latitud) if paciente.latitud else '',
            'longitud': float(paciente.longitud) if paciente.longitud else '',
            'tipo_sangre': paciente.tipo_sangre.tipo if paciente.tipo_sangre else '',
            'foto_url': paciente.get_image,

            # Historia clínica
            'antecedentes_personales': paciente.antecedentes_personales,
            'antecedentes_quirurgicos': paciente.antecedentes_quirurgicos,
            'antecedentes_familiares': paciente.antecedentes_familiares,
            'alergias': paciente.alergias,
            'medicamentos_actuales': paciente.medicamentos_actuales,
            'habitos_toxicos': paciente.habitos_toxicos,
            'vacunas': paciente.vacunas,
            'antecedentes_gineco_obstetricos': paciente.antecedentes_gineco_obstetricos,

            # Atenciones anteriores
            'atenciones': atenciones,
            'total_atenciones': paciente.atenciones.count()
        }

        return {
            'paciente_data': paciente_data,
            'paciente_json': json.dumps(paciente_data)
        }

    except Paciente.DoesNotExist:
        return {
            'paciente_data': '',
            'paciente_json': 'null'
        }