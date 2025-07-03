from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import spacy
from django.urls import reverse  # Import reverse
from django.db.models import Q  # Import Q for complex queries

from applications.core.models import Medicamento, Paciente, Doctor

nlp = spacy.load("es_core_news_sm")


@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        query = data.get("query", "").lower()
        doc = nlp(query)  # Process the lowercased query

        print(f"Query: {query}")
        print(f"Lemmas: {[token.lemma_ for token in doc]}")
        print(f"Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")

        lemmas = [token.lemma_ for token in doc]
        response_data = {
            "message": "Lo siento, no pude entender tu solicitud. ¿Podrías ser más específico o intentar con una de las sugerencias?",
            "buttons": [],
        }

        # --- Helper functions for entity extraction ---
        def extract_medicamento_name(query_doc):
            specific_name = None
            # Prioritize spaCy entities that might represent products or miscellaneous items
            for ent in query_doc.ents:
                if ent.label_ in ["PROD", "MISC"]:
                    specific_name = ent.text
                    break

            # Fallback: clean the query from common keywords and use the remaining text
            if not specific_name:
                cleaned_query = query_doc.text
                # Keywords to remove from the query to isolate the medicine name
                keywords_to_remove = [
                    "medicamento",
                    "medicina",
                    "farmacia",
                    "buscar",
                    "encontrar",
                    "que",
                    "cuales",
                    "tienes",
                    "hay",
                    "un",
                    "una",
                    "el",
                    "la",
                    "los",
                    "las",
                    "quiero",
                    "necesito",
                    "dame",
                    "sobre",
                    "acerca de",
                ]
                for keyword in keywords_to_remove:
                    cleaned_query = cleaned_query.replace(keyword, "").strip()

                # Remove extra spaces that might result from replacements
                cleaned_query = " ".join(cleaned_query.split())

                if cleaned_query and len(cleaned_query.split()) > 0:
                    specific_name = cleaned_query
            return specific_name

        def extract_person_name(query_doc):
            for ent in query_doc.ents:
                if ent.label_ == "PER":
                    return ent.text
            return None

        # --- Intent Handlers ---
        def handle_medicamento_intent(query_doc, query_lemmas, original_query):
            specific_medicamento_name = extract_medicamento_name(query_doc)
            general_medicamento_keywords = [
                "qué",
                "cuales",
                "disponibles",
                "tienes",
                "hay",
            ]
            is_general_query = any(
                keyword in query_lemmas for keyword in general_medicamento_keywords
            )

            if (
                "mostrar" in query_lemmas
                and "todos" in query_lemmas
                and "medicamentos" in query_lemmas
            ):
                medicamentos = Medicamento.objects.filter(activo=True)
                if medicamentos.exists():
                    nombres_medicamentos = [m.nombre for m in medicamentos]
                    return {
                        "message": "Estos son los medicamentos disponibles en nuestro sistema: "
                        + ", ".join(nombres_medicamentos)
                        + "."
                    }
                else:
                    return {
                        "message": "Actualmente no hay medicamentos registrados en el sistema."
                    }
            elif specific_medicamento_name or is_general_query:
                if is_general_query:
                    return {"message": "Claro, puedo ayudarte con los medicamentos. ¿Cuál medicamento te interesa específicamente?"}
                elif specific_medicamento_name:
                    try:
                        # First, try an exact match with the original query
                        medicamento = Medicamento.objects.filter(nombre__iexact=original_query, activo=True).first()
                        if medicamento:
                            return {"message": f'Sí, tenemos {medicamento.nombre} en stock. Actualmente hay {medicamento.cantidad} unidades disponibles. Tipo: {medicamento.tipo.nombre}, Marca: {medicamento.marca_medicamento.nombre if medicamento.marca_medicamento else "N/A"}, Concentración: {medicamento.concentracion}, Vía de Administración: {medicamento.via_administracion}.'}
                        else:
                            # If no exact match, try similar names using the extracted specific_medicamento_name
                            medicamentos_similar = Medicamento.objects.filter(nombre__icontains=specific_medicamento_name, activo=True)
                            if medicamentos_similar.count() == 1:
                                medicamento = medicamentos_similar.first()
                                return {"message": f'No encontré "{original_query}" exactamente, pero encontré {medicamento.nombre} en stock. Actualmente hay {medicamento.cantidad} unidades disponibles. Tipo: {medicamento.tipo.nombre}, Marca: {medicamento.marca_medicamento.nombre if medicamento.marca_medicamento else "N/A"}, Concentración: {medicamento.concentracion}, Vía de Administración: {medicamento.via_administracion}.'}
                            elif medicamentos_similar.count() > 1:
                                nombres_similares = [m.nombre for m in medicamentos_similar]
                                return {"message": f'Encontré varios medicamentos similares a "{original_query}": {", ".join(nombres_similares)}. ¿Cuál te interesa específicamente?'}
                            else:
                                return {"message": f'No encontré el medicamento "{original_query}" en nuestro sistema. ¿Estás seguro de que el nombre es correcto? Si deseas ver todos los medicamentos disponibles, puedes preguntar "mostrar todos los medicamentos".'}
                    except Exception as e:
                        return {"message": f'Hubo un error al buscar el medicamento: {e}'}
            return None

        def handle_paciente_intent(query_doc, query_lemmas, original_query):
            specific_paciente_name = extract_person_name(query_doc)
            general_paciente_keywords = ["buscar", "encontrar", "registrado", "quién"]
            is_general_query = (
                any(keyword in query_lemmas for keyword in general_paciente_keywords)
                and not specific_paciente_name
            )

            if specific_paciente_name:
                try:
                    # Try exact match first
                    pacientes_exact = Paciente.objects.filter(
                        Q(nombres__iexact=specific_paciente_name, activo=True)
                        | Q(apellidos__iexact=specific_paciente_name, activo=True)
                    )
                    if " " in specific_paciente_name:
                        first_name, last_name = specific_paciente_name.split(" ", 1)
                        pacientes_exact = pacientes_exact | Paciente.objects.filter(
                            Q(nombres__iexact=first_name, activo=True),
                            Q(apellidos__iexact=last_name, activo=True),
                        )

                    if pacientes_exact.exists():
                        paciente = pacientes_exact.first()
                        return {
                            "message": f'Sí, el paciente {paciente.nombres} {paciente.apellidos} está registrado en nuestro sistema. Cédula: {paciente.cedula_ecuatoriana}, Teléfono: {paciente.telefono}, Email: {paciente.email if paciente.email else "N/A"}, Tipo de Sangre: {paciente.tipo_sangre.tipo if paciente.tipo_sangre else "N/A"}.'
                        }
                    else:
                        # If no exact match, try similar names
                        pacientes_similar = Paciente.objects.filter(
                            Q(nombres__icontains=specific_paciente_name, activo=True)
                            | Q(
                                apellidos__icontains=specific_paciente_name, activo=True
                            )
                        )
                        if pacientes_similar.count() == 1:
                            paciente = pacientes_similar.first()
                            return {
                                "message": f'No encontré "{specific_paciente_name}" exactamente, pero encontré al paciente {paciente.nombres} {paciente.apellidos} en nuestro sistema. Cédula: {paciente.cedula_ecuatoriana}, Teléfono: {paciente.telefono}, Email: {paciente.email if paciente.email else "N/A"}, Tipo de Sangre: {paciente.tipo_sangre.tipo if paciente.tipo_sangre else "N/A"}.'
                            }
                        elif pacientes_similar.count() > 1:
                            nombres_similares = [
                                f"{p.nombres} {p.apellidos}" for p in pacientes_similar
                            ]
                            return {
                                "message": f'Encontré varios pacientes similares a "{specific_paciente_name}": {", ".join(nombres_similares)}. ¿Cuál te interesa específicamente?'
                            }
                        else:
                            return {
                                "message": f'No encontré al paciente "{specific_paciente_name}" en nuestros registros. Por favor, verifica el nombre.'
                            }
                except Exception as e:
                    return {"message": f"Hubo un error al buscar al paciente: {e}"}
            elif is_general_query:
                return {
                    "message": "Para buscar un paciente, por favor, dime su nombre completo o al menos su primer nombre."
                }
            else:
                return {
                    "message": "Mencionaste un paciente, pero no pude identificar el nombre. Por favor, dime el nombre exacto del paciente que buscas."
                }
            return None

        def handle_doctor_intent(query_doc, query_lemmas, original_query):
            specific_doctor_name = extract_person_name(query_doc)
            general_doctor_keywords = ["cuál", "horario", "de", "un"]
            is_general_query = (
                any(keyword in query_lemmas for keyword in general_doctor_keywords)
                and not specific_doctor_name
            )

            if specific_doctor_name:
                try:
                    # Try exact match first
                    doctors_exact = Doctor.objects.filter(
                        Q(nombres__iexact=specific_doctor_name, activo=True)
                        | Q(apellidos__iexact=specific_doctor_name, activo=True)
                    )
                    if " " in specific_doctor_name:
                        first_name, last_name = specific_doctor_name.split(" ", 1)
                        doctors_exact = doctors_exact | Doctor.objects.filter(
                            Q(nombres__iexact=first_name, activo=True),
                            Q(apellidos__iexact=last_name, activo=True),
                        )

                    if doctors_exact.exists():
                        doctor = doctors_exact.first()
                        return {
                            "message": f'El horario de atención del Dr. {doctor.nombres} {doctor.apellidos} es: {doctor.horario_atencion}. Especialidad: {", ".join([e.nombre for e in doctor.especialidad.all()])}. Teléfono: {doctor.telefonos}.'
                        }
                    else:
                        # If no exact match, try similar names
                        doctors_similar = Doctor.objects.filter(
                            Q(nombres__icontains=specific_doctor_name, activo=True)
                            | Q(apellidos__icontains=specific_doctor_name, activo=True)
                        )
                        if doctors_similar.count() == 1:
                            doctor = doctors_similar.first()
                            return {
                                "message": f'No encontré "{specific_doctor_name}" exactamente, pero encontré al Dr. {doctor.nombres} {doctor.apellidos}. Su horario de atención es: {doctor.horario_atencion}. Especialidad: {", ".join([e.nombre for e in doctor.especialidad.all()])}. Teléfono: {doctor.telefonos}.'
                            }
                        elif doctors_similar.count() > 1:
                            nombres_similares = [
                                f"{d.nombres} {d.apellidos}" for d in doctors_similar
                            ]
                            return {
                                "message": f'Encontré varios doctores similares a "{specific_doctor_name}": {", ".join(nombres_similares)}. ¿Cuál te interesa específicamente?'
                            }
                        else:
                            return {
                                "message": f'No encontré al Dr. "{specific_doctor_name}" en nuestro sistema. ¿Podrías verificar el nombre?'
                            }
                except Doctor.DoesNotExist:
                    return {
                        "message": f'No encontré al Dr. "{specific_doctor_name}" en nuestro sistema. ¿Podrías verificar el nombre?'
                    }
                except Exception as e:
                    return {"message": f"Hubo un error al buscar al doctor: {e}"}
            elif is_general_query:
                return {
                    "message": "Para consultar el horario de un doctor, por favor, dime su nombre."
                }
            else:
                return {
                    "message": "Mencionaste un doctor, pero no pude identificar el nombre. Por favor, dime el nombre exacto del doctor para ver su horario."
                }
            return None

        def handle_add_entity_intent(query_doc, query_lemmas, original_query):
            entity_creation_urls = {
                "paciente": "core:paciente_create",
                "medicamento": "core:medicamento_create",
                "doctor": "core:doctor_create",
                "empleado": "core:empleado_create",
                "cargo": "core:cargo_create",
                "especialidad": "core:especialidad_create",
                "diagnostico": "core:diagnostico_create",
                "tipo de sangre": "core:tipo_sangre_create",
                "tipo de medicamento": "core:tipo_medicamento_create",
                "marca de medicamento": "core:marca_medicamento_create",
                "tipo de gasto": "core:tipo_gasto_create",
                "gasto mensual": "core:gasto_mensual_create",
            }

            found_entity = None
            for entity, url_name in entity_creation_urls.items():
                if entity in query_doc.text:
                    found_entity = entity
                    break

            if found_entity and (
                "cómo" in query_lemmas
                or "añadir" in query_lemmas
                or "registrar" in query_lemmas
                or "crear" in query_lemmas
            ):
                try:
                    create_url = reverse(url_name)
                    return {
                        "message": f"Para añadir un nuevo {found_entity}, sigue estos pasos:\n1. Haz clic en el botón de abajo.\n2. Rellena el formulario con la información requerida.\n3. Guarda los cambios.",
                        "buttons": [
                            {
                                "text": f"Añadir {found_entity.capitalize()}",
                                "url": create_url,
                            }
                        ],
                    }
                except Exception as e:
                    return {
                        "message": f"Lo siento, no pude generar el enlace para añadir {found_entity}. Error: {e}"
                    }
            return None

        # --- Intent Dispatcher ---
        intents = [
            (
                "medicamento",
                [
                    "medicamento",
                    "medicina",
                    "farmacia",
                    "stock",
                    "disponible",
                    "comprar",
                    "vender",
                    "pastilla",
                    "jarabe",
                    "crema",
                    "dosis",
                ],
            ),
            (
                "paciente",
                [
                    "paciente",
                    "persona",
                    "cliente",
                    "registrado",
                    "historial",
                    "cita",
                    "nombre",
                    "apellido",
                ],
            ),
            (
                "doctor",
                [
                    "doctor",
                    "médico",
                    "horario",
                    "cita",
                    "especialista",
                    "consultorio",
                    "disponibilidad",
                ],
            ),
            (
                "add_entity",
                ["cómo", "añadir", "registrar", "crear", "ingresar", "nuevo"],
            ),
        ]

        # Determine intent based on keywords
        detected_intent = None
        for intent_name, keywords in intents:
            if any(keyword in lemmas for keyword in keywords):
                detected_intent = intent_name
                break

        if detected_intent == "medicamento":
            response = handle_medicamento_intent(doc, lemmas, query)
        elif detected_intent == "paciente":
            response = handle_paciente_intent(doc, lemmas, query)
        elif detected_intent == "doctor":
            response = handle_doctor_intent(doc, lemmas, query)
        elif detected_intent == "add_entity":
            response = handle_add_entity_intent(doc, lemmas, query)
        else:
            response = None  # No specific intent detected

        if response:
            response_data.update(response)
        else:
            response_data["message"] = (
                'Lo siento, no pude entender tu solicitud. Puedes intentar preguntar sobre:\n- "medicamentos disponibles" o el nombre de un medicamento.\n- "buscar paciente [nombre]" o "pacientes registrados".\n- "horario doctor [nombre]" o "doctores disponibles".\n- "cómo añadir un paciente" o "registrar un medicamento".'
            )
            # Add general suggestions or buttons here if desired

        return JsonResponse(response_data)

    return JsonResponse({"error": "Invalid request"}, status=400)
