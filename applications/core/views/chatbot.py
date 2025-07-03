from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import spacy

from applications.core.models import Medicamento, Paciente, Doctor

nlp = spacy.load('es_core_news_sm')

@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').lower()
        doc = nlp(query) # Process the lowercased query
        
        print(f"Query: {query}")
        print(f"Lemmas: {[token.lemma_ for token in doc]}")
        print(f"Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")

        response_message = 'Lo siento, no pude entender tu solicitud. ¿Podrías ser más específico o intentar con una de las sugerencias?'

        lemmas = [token.lemma_ for token in doc]

        # --- Extract potential medicine name early ---
        specific_medicamento_name = None
        
        # Prioritize direct medicine name if the query is short and not a general question
        question_words = ['qué', 'cuales', 'tienes', 'hay']
        if len(doc) <= 2 and not any(word in lemmas for word in question_words):
            specific_medicamento_name = query.strip()

        if not specific_medicamento_name:
            for ent in doc.ents:
                if ent.label_ in ['PROD', 'MISC', 'ORG', 'LOC', 'PER']:
                    specific_medicamento_name = ent.text
                    break
        if not specific_medicamento_name:
            cleaned_query = query
            for keyword in ['medicamento', 'medicina', 'farmacia', 'buscar', 'encontrar', 'que', 'cuales', 'tienes', 'hay', 'un', 'una', 'el', 'la', 'los', 'las']:
                cleaned_query = cleaned_query.replace(keyword, '').strip()
            if cleaned_query and len(cleaned_query.split()) > 0:
                specific_medicamento_name = cleaned_query
        print(f"Extracted specific_medicamento_name: {specific_medicamento_name}") # Debug print

        # --- Check for general medicine query ---
        general_medicamento_keywords = ['qué', 'cuales', 'disponibles', 'tienes', 'hay']
        is_general_query = any(keyword in lemmas for keyword in general_medicamento_keywords)

        # --- Intención: Medicamentos ---
        # Check if a specific medicine name was extracted or if it's a general query about medicines
        if specific_medicamento_name or is_general_query:
            if is_general_query:
                response_message = 'Claro, puedo ayudarte con los medicamentos. ¿Cuál medicamento te interesa específicamente?'
            elif specific_medicamento_name:
                print(f"Attempting to find medicine: {specific_medicamento_name}") # Debug print
                try:
                    medicamentos = Medicamento.objects.filter(nombre__icontains=specific_medicamento_name)
                    print(f"Medicamentos found with icontains: {medicamentos.count()}") # Debug print

                    if medicamentos.exists():
                        medicamento = medicamentos.filter(nombre__iexact=specific_medicamento_name).first()
                        if not medicamento:
                            medicamento = medicamentos.first()
                        response_message = f'Sí, tenemos {medicamento.nombre} en stock. Actualmente hay {medicamento.cantidad} unidades disponibles.'
                    else:
                        response_message = f'No encontré el medicamento "{specific_medicamento_name}" en nuestro sistema. ¿Estás seguro de que el nombre es correcto? Si deseas ver todos los medicamentos disponibles, puedes preguntar "mostrar todos los medicamentos".'
                except Exception as e:
                    response_message = f'Hubo un error al buscar el medicamento: {e}'
        # --- Intención: Pacientes ---
        elif 'paciente' in lemmas:
            specific_paciente_name = None
            for ent in doc.ents:
                if ent.label_ == 'PER': # Assuming patient names are persons
                    specific_paciente_name = ent.text
                    break

            general_paciente_keywords = ['buscar', 'encontrar', 'registrado', 'quién']
            is_general_query = any(keyword in lemmas for keyword in general_paciente_keywords) and not specific_paciente_name

            if specific_paciente_name:
                try:
                    # Try to match full name if query contains multiple words
                    paciente = Paciente.objects.filter(nombre__iexact=specific_paciente_name).first()
                    if not paciente:
                        paciente = Paciente.objects.filter(apellido__iexact=specific_paciente_name).first()
                    if not paciente and ' ' in specific_paciente_name:
                        # Try to match full name if query contains multiple words
                        first_name, last_name = specific_paciente_name.split(' ', 1)
                        paciente = Paciente.objects.filter(nombre__iexact=first_name, apellido__iexact=last_name).first()

                    if paciente:
                        response_message = f'Sí, el paciente {paciente.nombre} {paciente.apellido} está registrado en nuestro sistema.'
                    else:
                        response_message = f'No encontré al paciente "{specific_paciente_name}" en nuestros registros. Por favor, verifica el nombre.'
                except Exception as e: # Catch any other potential errors during lookup
                    response_message = f'Hubo un error al buscar al paciente: {e}'
            elif is_general_query:
                response_message = 'Para buscar un paciente, por favor, dime su nombre completo o al menos su primer nombre.'
            else:
                response_message = 'Mencionaste un paciente, pero no pude identificar el nombre. Por favor, dime el nombre exacto del paciente que buscas.'

        # --- Intención: Horario de Doctor ---
        elif 'horario' in lemmas and 'doctor' in lemmas:
            specific_doctor_name = None
            for ent in doc.ents:
                if ent.label_ == 'PER': # Assuming doctor names are persons
                    specific_doctor_name = ent.text
                    break

            general_doctor_keywords = ['cuál', 'horario', 'de', 'un']
            is_general_query = any(keyword in lemmas for keyword in general_doctor_keywords) and not specific_doctor_name

            if specific_doctor_name:
                try:
                    doctor = Doctor.objects.get(nombre__iexact=specific_doctor_name)
                    response_message = f'El horario de atención del Dr. {doctor.nombre} es: {doctor.horarios_atencion}.'
                except Doctor.DoesNotExist:
                    response_message = f'No encontré al Dr. "{specific_doctor_name}" en nuestro sistema. ¿Podrías verificar el nombre?'
            elif is_general_query:
                response_message = 'Para consultar el horario de un doctor, por favor, dime su nombre.'
            else:
                response_message = 'Mencionaste un doctor, pero no pude identificar el nombre. Por favor, dime el nombre exacto del doctor para ver su horario.'
        
        return JsonResponse({'message': response_message})

    return JsonResponse({'error': 'Invalid request'}, status=400)

