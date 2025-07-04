from django import forms
from django.forms import ModelForm
from applications.doctor.models import DetalleServicioAtencion
from applications.core.models import Servicio


class DetalleServicioAtencionForm(ModelForm):
    class Meta:
        model = DetalleServicioAtencion
        fields = [
            "servicio",
            "cantidad",
            "observaciones",
        ]
        widgets = {
            "servicio": forms.Select(attrs={
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "cantidad": forms.NumberInput(attrs={
                "placeholder": "1",
                "min": "1",
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "observaciones": forms.Textarea(attrs={
                "placeholder": "Observaciones sobre el servicio...",
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 resize-none",
                "rows": 2,
            }),
        }
        labels = {
            "servicio": "Servicio",
            "cantidad": "Cantidad",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = Servicio.objects.filter(activo=True).order_by('nombre')
        self.fields['servicio'].empty_label = "Seleccione un servicio"

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad
