from django import forms
from django.forms import ModelForm
from applications.core.models import Servicio


class ServicioForm(ModelForm):
    class Meta:
        model = Servicio
        fields = [
            "nombre",
            "descripcion",
            "precio",
            "activo",
        ]
        error_messages = {
            "nombre": {
                "unique": "Ya existe un servicio con este nombre.",
            },
        }
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej: Consulta General, Radiografía, Análisis de Sangre",
                "id": "id_nombre",
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "descripcion": forms.Textarea(attrs={
                "placeholder": "Descripción detallada del servicio...",
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 resize-none",
                "rows": 3,
            }),
            "precio": forms.NumberInput(attrs={
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0",
                "class": "block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600",
            }),
        }
        labels = {
            "nombre": "Nombre del Servicio",
            "descripcion": "Descripción",
            "precio": "Precio ($)",
            "activo": "Activo",
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre")
        if nombre:
            nombre = nombre.strip().title()
            if not nombre:
                raise forms.ValidationError("El nombre del servicio no puede estar vacío.")
            if len(nombre) < 3:
                raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
            return nombre
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is not None:
            if precio < 0:
                raise forms.ValidationError("El precio no puede ser negativo.")
            if precio > 999999.99:
                raise forms.ValidationError("El precio no puede ser mayor a $999,999.99.")
        return precio
