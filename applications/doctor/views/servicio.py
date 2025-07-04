from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from applications.security.components.mixin_crud import CreateViewMixin, DeleteViewMixin, ListViewMixin, PermissionMixin, UpdateViewMixin
from applications.core.forms.servicio import ServicioForm
from applications.core.models import Servicio
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q


class ServicioListView(PermissionMixin, ListViewMixin, ListView):
    template_name = 'core/servicio/list.html'
    model = Servicio
    context_object_name = 'servicios'
    permission_required = 'view_servicio'
    paginate_by = 10

    def get_queryset(self):
        q1 = self.request.GET.get('q')
        if q1 is not None:
            self.query.add(Q(nombre__icontains=q1), Q.OR)
            self.query.add(Q(descripcion__icontains=q1), Q.OR)
        return self.model.objects.filter(self.query).order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('doctor:servicio_create')
        return context


class ServicioCreateView(PermissionMixin, CreateViewMixin, CreateView):
    model = Servicio
    template_name = 'core/servicio/form.html'
    form_class = ServicioForm
    success_url = reverse_lazy('doctor:servicio_list')
    permission_required = 'add_servicio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Grabar Servicio'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        servicio = self.object
        messages.success(self.request, f"Éxito al crear el servicio {servicio.nombre}.")
        return response


class ServicioUpdateView(PermissionMixin, UpdateViewMixin, UpdateView):
    model = Servicio
    template_name = 'core/servicio/form.html'
    form_class = ServicioForm
    success_url = reverse_lazy('doctor:servicio_list')
    permission_required = 'change_servicio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Actualizar Servicio'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        servicio = self.object
        messages.success(self.request, f"Éxito al actualizar el servicio {servicio.nombre}.")
        return response


class ServicioDeleteView(PermissionMixin, DeleteViewMixin, DeleteView):
    model = Servicio
    template_name = 'components/delete.html'
    success_url = reverse_lazy('doctor:servicio_list')
    permission_required = 'delete_servicio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Eliminar Servicio'
        context['description'] = f"¿Desea eliminar el servicio: {self.object.nombre}?"
        context['back_url'] = self.success_url
        context['has_dependencies'] = False # Asumimos que no hay dependencias por ahora
        return context

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except ProtectedError as e:
            servicio = self.get_object()
            messages.error(
                request, 
                f"No se puede eliminar el servicio '{servicio.nombre}' porque tiene registros asociados."
            )
            return HttpResponseRedirect(self.success_url)
