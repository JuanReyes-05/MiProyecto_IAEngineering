# DOCUMENTO TÉCNICO

## Agente Inteligente de Mesa de Ayuda

**Institución Financiera — Área de Helpdesk**
*Propuesta de Arquitectura, Fases de Implementación y Análisis de Costos*

> **Versión 1.0** | Abril 2026 | *Clasificación: Interno Confidencial*

---

## 1. Resumen Ejecutivo

El área de Mesa de Ayuda (Helpdesk) de la institución atiende actualmente todos los casos internos de los trabajadores de forma manual, dependiendo del criterio humano para clasificar, responder o escalar cada solicitud. Este documento propone la implementación de un **Agente Inteligente basado en Inteligencia Artificial** que automatice este proceso de extremo a extremo, integrándose con el sistema **ServisDesk** ya existente y manteniendo estrictos estándares de seguridad requeridos en el sector financiero.

### Problema actual

| Dimensión | Situación actual |
|---|---|
| **Clasificación** | 100% manual — dependiente de la disponibilidad del operador |
| **Tiempo de respuesta** | Variable; sin SLA garantizado en horas pico |
| **Conocimiento** | No existe base de conocimiento estructurada; el historial de correos no se reutiliza |
| **Derivaciones** | Derivación manual a TI Infraestructura y otras áreas sin trazabilidad centralizada |
| **Escalabilidad** | El volumen de tickets no puede crecer sin aumentar el personal del área |

### Propuesta de valor

El agente propuesto permite:

- Automatizar entre el **60% y el 80%** de los tickets de primer nivel
- Reducir el tiempo de respuesta a minutos
- Derivar automáticamente casos similares con historial adjunto
- Generar una base de conocimiento viva a partir de los correos ya resueltos

> Todo esto **sin reemplazar al equipo humano**, sino potenciando su capacidad de atención en casos complejos.

---

## 2. Alcance del Sistema

El sistema contempla los siguientes componentes funcionales:

- **Recepción de correos** enviados a `mesa_ayuda` y creación automática de tickets vía ServisDesk (integración con webhook o API)
- **Clasificación inteligente** de la solicitud: duda puntual, incidente técnico, o derivación a área específica
- **Resolución automática** de dudas puntuales mediante consulta al motor RAG (manuales e historial de correos resueltos)
- **Derivación automatizada** con contexto cuando se detecta similitud con casos previamente escalados a TI Infraestructura u otras áreas
- **Capa de seguridad en tres fases**: perimetral, protección de datos financieros (PII), y hardening avanzado
- **Panel de observabilidad** con trazabilidad de decisiones, costos por ticket y métricas de desempeño

> **Fuera de alcance (versión inicial):** atención de solicitudes externas, integración con canales distintos al correo electrónico, y modificación del sistema ServisDesk existente.

---

## 3. Clasificación por Etapas y Quick Wins

La implementación se divide en **cuatro etapas** ordenadas por impacto y complejidad. Las primeras dos etapas constituyen los *quick wins* que permiten mostrar valor a gerencia en las primeras semanas sin comprometer la estabilidad del sistema productivo.

### Etapa 0 — Quick Win 1: Clasificador de correos *(Semanas 1–3)*

| Atributo | Detalle |
|---|---|
| **Objetivo** | Clasificar automáticamente cada correo entrante en: Duda puntual / Incidente TI / Derivar a área |
| **Tecnología** | FastAPI + LangChain + Prompt Engineering few-shot con ejemplos reales del área |
| **Entregable** | API que recibe texto del correo y devuelve categoría + área sugerida + nivel de confianza |
| **Esfuerzo** | 2–3 semanas. Bajo riesgo. Sin impacto en producción. |
| **Valor demostrable** | Reducción inmediata del tiempo de triaje. Evidencia tangible para la gerencia. |

### Etapa 1 — Quick Win 2: Motor RAG con historial *(Semanas 4–7)*

| Atributo | Detalle |
|---|---|
| **Objetivo** | Indexar manuales institucionales y correos resueltos. Habilitar respuesta automática a dudas puntuales. |
| **Tecnología** | LangChain RAG + Base Vectorial (Chroma/Qdrant) + Embeddings OpenAI o modelo local |
| **Entregable** | Pipeline de ingesta: manuales PDF + correos históricos categorizados. Motor de búsqueda semántica. |
| **Esfuerzo** | 3–4 semanas. Requiere acceso a correos históricos resueltos (muestra mínima: 200 casos). |
| **Valor demostrable** | El agente puede responder consultas frecuentes sin intervención humana. Medible desde el primer día. |

### Etapa 2 — Agente completo con derivación *(Semanas 8–13)*

| Atributo | Detalle |
|---|---|
| **Objetivo** | Integrar clasificador + RAG + lógica de derivación automática en un agente orquestador único |
| **Tecnología** | LangChain Agents + FastAPI + ServisDesk API/webhook + Evaluador QA automático |
| **Entregable** | Agente funcional en ambiente de pruebas con casos reales. Métricas de precisión de derivación vs. historial manual. |
| **Esfuerzo** | 5–6 semanas. Requiere coordinación con TI Infraestructura para validar reglas de derivación. |
| **Riesgo** | Medio. Derivaciones incorrectas deben tener flujo de revisión humana antes de pasar a producción. |

### Etapa 3 — Hardening, observabilidad y producción *(Semanas 14–20)*

| Atributo | Detalle |
|---|---|
| **Objetivo** | Despliegue dockerizado, seguridad avanzada, monitoreo de costos y caché de respuestas frecuentes |
| **Tecnología** | Docker + LocalStack + Observabilidad (tracing) + Vault de secretos + RBAC + Optimización de costos |
| **Entregable** | Sistema en producción con SLA definido, panel de métricas para gerencia y políticas de retención de datos. |
| **Esfuerzo** | 6–7 semanas. Involucra a Ciberseguridad y Cumplimiento para validar controles financieros. |

### Línea de tiempo consolidada

| Etapa | Semanas | Estado | Dependencia clave | Entregable a gerencia |
|---|---|---|---|---|
| **Etapa 0** | 1–3 | Quick Win | Ejemplos de correos categorizados | Demo: clasificador en vivo |
| **Etapa 1** | 4–7 | Quick Win | Acceso a 200+ correos históricos | Demo: respuesta automática RAG |
| **Etapa 2** | 8–13 | Beta controlada | API ServisDesk + validación TI Infra | Reporte de precisión de derivación |
| **Etapa 3** | 14–20 | Producción | Ciberseguridad + Cumplimiento | Panel de métricas y costos en vivo |

---

## 4. Arquitectura Técnica

La arquitectura se diseñó bajo tres principios rectores:

1. **Mínima fricción** con los sistemas existentes (ServisDesk se mantiene intacto)
2. **Defensa en profundidad** en tres fases de seguridad
3. **Trazabilidad completa** de cada decisión del agente para cumplimiento regulatorio financiero

### 4.1 Componentes principales

| Componente | Tecnología | Función |
|---|---|---|
| **API Gateway** | FastAPI + JWT interno | Punto único de entrada. Autenticación, rate limiting y logging de toda solicitud entrante. |
| **Agente Orquestador** | LangChain Agents | Coordina el flujo: parseo del correo, decisión de ruta (responder/derivar) y generación de respuesta. |
| **Motor RAG** | LangChain + Embeddings | Recupera fragmentos relevantes de manuales y correos históricos para contextualizar la respuesta. |
| **Base Vectorial** | Chroma o Qdrant | Almacena embeddings de documentos. Soporta búsqueda semántica con filtros por área y fecha. |
| **Clasificador** | LangChain + Prompt Engineering | Determina si el caso es duda puntual, incidente técnico o requiere derivación, con score de confianza. |
| **Evaluador QA** | LangChain Evaluators | Valida la calidad de las respuestas generadas y detecta posibles alucinaciones antes de enviar. |
| **Módulo PII** | Regex + NER | Detecta y redacta datos sensibles (números de cuenta, cédulas, nombres) antes de enviarlos al LLM. |
| **Caché semántico** | Redis + similitud coseno | Evita llamadas repetidas al LLM para consultas frecuentes. Reduce costos hasta 60%. |

### 4.2 Flujo de procesamiento de un ticket

1. El trabajador envía correo a `mesa_ayuda@empresa.com`.
2. ServisDesk crea el ticket y emite un **webhook** al API Gateway del agente.
3. El módulo **PII** intercepta el texto y redacta datos sensibles antes de cualquier procesamiento por LLM.
4. El **clasificador** determina la intención y la categoría del caso.
5. **Si es duda puntual:** el motor RAG recupera contexto relevante y el agente genera la respuesta. El Evaluador QA valida la respuesta. Se envía el correo de respuesta y se cierra el ticket.
6. **Si hay similitud con casos previos de TI Infraestructura** *(score > 0.85)*: se deriva automáticamente con contexto del caso similar adjunto.
7. **Si es una categoría distinta:** se clasifica el área de destino y se deriva con el resumen del caso.
8. Todo el *trace* (decisiones, documentos recuperados, scores, costo en tokens) queda registrado en el **log de auditoría**.

---

## 5. Seguridad por Fases

Dado que el sistema opera en una institución financiera y procesa comunicaciones internas sensibles, la seguridad **no es una capa adicional sino parte del diseño central**. Se implementa en tres fases progresivas alineadas con el ciclo de despliegue.

### Fase 1 — Seguridad perimetral *(Etapa 0–1)*

- **TLS 1.3** en todas las comunicaciones entre componentes del sistema
- Autenticación **JWT interna** para llamadas entre microservicios
- **Rate limiting**: máximo de solicitudes por IP y por usuario en ventana de tiempo
- **Web Application Firewall (WAF)** delante del API Gateway
- Validación y sanitización de todos los inputs antes de procesamiento

### Fase 2 — Protección de datos financieros y PII *(Etapa 1–2)*

- Módulo de detección y redacción de **PII**: números de cuenta, cédulas, RUC, nombres completos, montos
- Cifrado **AES-256** en reposo para la base vectorial y logs de auditoría
- **Política de no persistencia**: el LLM nunca recibe datos personales sin redacción previa
- **Audit log inmutable** de cada decisión del agente con timestamp, ticket ID y área de destino
- Separación de ambientes: producción, staging y desarrollo con accesos **RBAC** diferenciados

### Fase 3 — Hardening avanzado *(Etapa 3)*

- Gestión de secretos con **HashiCorp Vault**: claves de API, credenciales de base de datos, certificados
- **SAST** (análisis estático) y **DAST** (análisis dinámico) integrados en el pipeline de CI/CD
- Políticas de retención de datos financieros alineadas con normativa **SBS** y regulación local
- Revisión periódica de permisos RBAC con principio de **mínimo privilegio**
- **Pruebas de penetración** antes del pase a producción

### Puntos críticos de seguridad para gerencia

| Riesgo | Nivel | Control implementado |
|---|---|---|
| Exposición de datos de trabajadores al LLM externo | 🔴 **ALTO** | Módulo PII redacta todos los datos sensibles antes de enviar al modelo |
| Acceso no autorizado al historial de tickets | 🔴 **ALTO** | RBAC estricto: cada área solo accede a sus propios tickets. Audit log inmutable. |
| Respuestas incorrectas del agente (alucinaciones) | 🟡 **MEDIO** | Evaluador QA automático + umbral de confianza; si no se supera, escala a humano |
| Inyección de prompt maliciosa en el cuerpo del correo | 🟡 **MEDIO** | Sanitización de inputs + instrucciones de sistema que previenen override de rol del agente |
| Dependencia de proveedor externo de LLM | 🟢 **BAJO** | Arquitectura desacoplada permite migrar a modelo local (Llama, Mistral) sin rediseño |

---

## 6. Análisis de Costos

El análisis de costos considera tres dimensiones: **infraestructura**, **inferencia del LLM**, y **optimizaciones** implementadas para reducir el gasto operativo mensual.

### 6.1 Estimación de costos de inferencia por ticket

Los costos de inferencia dependen del volumen de tokens procesados. Un ticket promedio de Helpdesk genera aproximadamente **800 tokens de entrada** (correo + contexto RAG) y **300 tokens de salida** (respuesta generada).

| Componente de costo | Tokens promedio | Costo USD/ticket | Optimización disponible |
|---|---|---|---|
| Llamada al clasificador | ~400 tokens | ~$0.0005 | Caché semántico: si ya se clasificó texto similar, reutiliza resultado |
| Consulta RAG + respuesta | ~1100 tokens | ~$0.0018 | Caché de 24h: consultas frecuentes no llaman al LLM. Ahorro estimado 60%. |
| Evaluador QA | ~500 tokens | ~$0.0008 | Sólo se ejecuta si el clasificador supera umbral de derivación automática |
| **TOTAL sin caché** | **~2000 tokens** | **~$0.003** | — |
| **TOTAL con caché activo** | **~800 tokens** | **~$0.0012** | Estimado con 60% de tickets respondidos desde caché |

### 6.2 Proyección mensual por volumen de tickets

| Escenario | Tickets/mes | Sin caché (USD) | Con caché (USD) | Ahorro mensual (USD) |
|---|---|---|---|---|
| Volumen bajo | 500 | $1.50 | $0.60 | $0.90 |
| Volumen medio | 2,000 | $6.00 | $2.40 | $3.60 |
| Volumen alto | 10,000 | $30.00 | $12.00 | $18.00 |

### 6.3 Retorno sobre la inversión (ROI)

> El costo de inferencia del LLM es **marginal** comparado con el costo del tiempo operativo que se libera.

Asumiendo que un operador dedica en promedio **8 minutos** por ticket de primer nivel, y que el agente automatiza el **70%** de esos tickets:

| Métrica | Estimado |
|---|---|
| Tickets automatizables al mes *(70% de 2,000)* | **1,400 tickets** |
| Horas liberadas al mes | **186 horas operativas** |
| Costo de infraestructura mensual *(servidor + BD)* | ~$80–$150 USD/mes (nube o servidor propio) |
| Costo de inferencia LLM mensual *(con caché)* | ~$2.40 USD/mes (2,000 tickets) |
| Tiempo de recuperación de inversión de desarrollo | Estimado **3–4 meses** desde pase a producción |

---

## 7. Puntos Críticos a Considerar

Los siguientes puntos requieren **decisión o validación por parte de gerencia** antes o durante la implementación:

### 7.1 Datos y conocimiento

- **Acceso a correos históricos resueltos:** se necesita una muestra mínima de **200 casos etiquetados** por área de destino para entrenar el clasificador y poblar la base vectorial inicial. Este es el insumo más crítico del sistema.
- **Gobernanza de manuales:** se debe definir qué documentos son fuente de verdad y quién es responsable de mantenerlos actualizados en la base de conocimiento.
- **Privacidad de correos históricos:** antes de indexar correos previos, se recomienda validar con Cumplimiento que el procesamiento de ese historial es consistente con las políticas internas de privacidad de la institución.

### 7.2 Integración con ServisDesk

- La integración depende de que ServisDesk exponga una **API o soporte webhooks**. Si el sistema solo envía notificaciones por correo, se puede usar un mecanismo alternativo de *polling* de buzón, pero agrega latencia.
- Se debe definir el flujo de **actualización de ticket**: quién cierra el ticket cuando el agente responde automáticamente, y cómo se registra la respuesta en el historial de ServisDesk.

### 7.3 Umbrales de derivación y supervisión humana

- El **umbral de confianza** para derivación automática *(propuesto: 0.85)* debe ser calibrado con datos reales durante la fase beta. Un umbral muy bajo genera falsas derivaciones; uno muy alto reduce la automatización.
- Se recomienda un periodo de **supervisión humana de 4 semanas** en la Etapa 2 donde los operadores validen las decisiones del agente antes de que estas sean definitivas. Esto permite ajustar el umbral con base en evidencia real.

### 7.4 Modelo de lenguaje (LLM)

- La propuesta inicial usa un **LLM externo vía API** (OpenAI, Anthropic o equivalente). Para el sector financiero, se debe evaluar si es admisible enviar texto de tickets (redactado de PII) a un proveedor externo, o si la política de seguridad requiere un **modelo local** (Llama 3, Mistral).
- La arquitectura está diseñada para ser **agnóstica al proveedor** del LLM. El cambio a un modelo local en etapas posteriores no requiere rediseño del sistema.

### 7.5 Cambio organizacional

- El equipo de Helpdesk debe **participar activamente** en la validación de los ejemplos de clasificación y en la revisión durante la fase beta. Sin su participación, el sistema no aprenderá las particularidades del área.
- Se recomienda comunicar el propósito del agente como una **herramienta de asistencia** que libera al equipo de tareas repetitivas, **no como un reemplazo de personal**.

---

## 8. Recomendaciones y Próximos Pasos

| # | Acción | Responsable sugerido | Plazo |
|---|---|---|---|
| 1 | Confirmar acceso a 200 correos históricos etiquetados por área | Helpdesk + TI Infraestructura | Semana 1 |
| 2 | Verificar si ServisDesk expone API/webhook para integración | TI Infraestructura | Semana 1 |
| 3 | Validar con Cumplimiento el procesamiento de correos históricos | Cumplimiento + Legal | Semana 1–2 |
| 4 | Aprobar uso de LLM externo (API) o definir requisito de modelo local | Ciberseguridad + Gerencia TI | Semana 2 |
| 5 | Iniciar Etapa 0: desarrollo del clasificador con ejemplos reales | Equipo de desarrollo AI | Semana 2–4 |
| 6 | Definir SLA objetivo para tickets automatizados vs. derivados | Gerencia Helpdesk | Semana 3 |

### Criterios de éxito medibles

- **Etapa 0:** el clasificador alcanza **>90% de precisión** en el conjunto de validación de correos históricos.
- **Etapa 1:** al menos el **40% de los tickets de duda puntual** son respondidos automáticamente sin intervención humana.
- **Etapa 2:** el **70% de los casos de TI Infraestructura** son derivados correctamente con contexto en menos de **2 minutos**.
- **Etapa 3:** el costo por ticket con caché activo no supera **$0.002 USD**. Tiempo de respuesta promedio menor a **3 minutos**.

---

*Fin del documento*
