"""Plantillas de prompts usadas por los services de generación y scoring."""

PROMPT_SISTEMA = """Eres un asistente de soporte al cliente profesional y empático.
Tu única fuente de información es el contexto que se te proporciona a continuación.

REGLAS IMPORTANTES:
1. Responde ÚNICAMENTE basándote en el contexto proporcionado.
2. Si el contexto no contiene información suficiente para responder, di exactamente:
   "Lo siento, no tengo información suficiente sobre ese tema en mi base de conocimiento."
3. No inventes información ni uses conocimiento externo.
4. Sé conciso pero completo. Máximo 3-4 párrafos.
5. Si hay pasos a seguir, usa una lista numerada.
6. Mantén un tono amigable y profesional.

CONTEXTO DE LA BASE DE CONOCIMIENTO:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta}

RESPUESTA:"""

PROMPT_SCORE = """Evalúa qué tan bien responde el siguiente texto a la pregunta dada.
Devuelve SOLO un número decimal entre 0.0 y 1.0, sin texto adicional.

0.0 = No hay información relevante / dice que no sabe
0.5 = Información parcial o poco específica
1.0 = Respuesta completa y directa

Pregunta: {pregunta}
Respuesta: {respuesta}

Score (solo el número):"""

PROMPT_DERIVACION = """Analiza el siguiente mensaje de un usuario y decide si su caso requiere derivar el ticket a 2do nivel o puede resolverse con una respuesta directa.

Devuelve SOLO "si" o "no", sin texto adicional.

"si" = El caso requiere seguimiento: reclamo, falla técnica persistente, reembolso, queja formal, situación que necesita acción por parte de un agente humano.
"no" = El caso puede resolverse con información: consulta, pregunta, duda, solicitud de instrucciones.

Mensaje del usuario: {pregunta}

¿Requiere ticket de seguimiento? (si/no):"""

FRASES_SIN_INFO = (
    "no tengo información suficiente",
    "no tengo información sobre",
    "no encontré información",
    "no puedo responder",
)
