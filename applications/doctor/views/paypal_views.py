import json
import paypalrestsdk
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from applications.doctor.models import Atencion, Pago, DetallePago
from applications.core.models import Medicamento, Servicio
from decimal import Decimal

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # sandbox or live
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@csrf_exempt
@require_POST
def create_paypal_order(request):
    try:
        data = json.loads(request.body)
        atencion_id = data.get('atencion_id')

        if not atencion_id:
            return JsonResponse({'error': 'ID de atención no proporcionado.'}, status=400)

        try:
            atencion = Atencion.objects.get(pk=atencion_id)
            pago = Pago.objects.get(atencion=atencion)
        except Atencion.DoesNotExist:
            return JsonResponse({'error': 'Atención no encontrada.'}, status=404)
        except Pago.DoesNotExist:
            return JsonResponse({'error': 'Pago no encontrado para esta atención.'}, status=404)

        total_amount = pago.monto_total

        # Crear la orden de PayPal
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": "http://localhost:8000/paypal/execute/",  # Placeholder, se manejará en el frontend
                "cancel_url": "http://localhost:8000/paypal/cancel/"   # Placeholder
            },
            "transactions": [{
                "amount": {
                    "total": str(total_amount.quantize(Decimal('0.01'))),  # Formato con 2 decimales
                    "currency": "USD"
                },
                "description": f"Pago por atención médica y servicios para {atencion.paciente.nombre_completo}"
            }]
        })

        if payment.create():
            return JsonResponse({'paypal_order_id': payment.id, 'approval_url': payment.links[0]['href']})
        else:
            return JsonResponse({'error': payment.error}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def capture_paypal_payment(request):
    try:
        data = json.loads(request.body)
        paypal_order_id = data.get('paypal_order_id')
        payer_id = data.get('payer_id')
        atencion_id = data.get('atencion_id')

        if not paypal_order_id or not payer_id or not atencion_id:
            return JsonResponse({'error': 'Faltan parámetros de PayPal o ID de atención.'}, status=400)

        try:
            atencion = Atencion.objects.get(pk=atencion_id)
        except Atencion.DoesNotExist:
            return JsonResponse({'error': 'Atención no encontrada.'}, status=404)

        payment = paypalrestsdk.Payment.find(paypal_order_id)

        if payment.execute({"payer_id": payer_id}):
            # Actualizar el estado del pago en tu base de datos
            # Aquí deberías crear o actualizar tu modelo Pago
            total_amount = Decimal(payment.transactions[0].amount.total)

            pago, created = Pago.objects.get_or_create(
                atencion=atencion,
                defaults={
                    'metodo_pago': 'paypal',
                    'monto_total': total_amount,
                    'estado': 'pagado',
                    'paypal_order_id': paypal_order_id,
                    'paypal_capture_id': payment.transactions[0].related_resources[0].sale.id if payment.transactions[0].related_resources else None,
                    'nombre_pagador': payment.payer.payer_info.first_name + " " + payment.payer.payer_info.last_name if payment.payer.payer_info.first_name else payment.payer.payer_info.email,
                    'json_respuesta_paypal': json.dumps(payment.to_dict())
                }
            )
            if not created:
                pago.metodo_pago = 'paypal'
                pago.monto_total = total_amount
                pago.estado = 'pagado'
                pago.paypal_order_id = paypal_order_id
                pago.paypal_capture_id = payment.transactions[0].related_resources[0].sale.id if payment.transactions[0].related_resources else None
                pago.nombre_pagador = payment.payer.payer_info.first_name + " " + payment.payer.payer_info.last_name if payment.payer.payer_info.first_name else payment.payer.payer_info.email
                pago.json_respuesta_paypal = json.dumps(payment.to_dict())
                pago.save()

            return JsonResponse({'status': 'success', 'message': 'Pago procesado exitosamente.', 'pago_id': pago.id})
        else:
            return JsonResponse({'status': 'error', 'message': payment.error}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
