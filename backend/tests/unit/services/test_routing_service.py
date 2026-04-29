"""Tests del RoutingService — reglas de decisión del agente."""
from app.schemas.enums import AccionRouter
from app.services.routing_service import RoutingServiceImpl


def test_palabra_de_escalacion_siempre_escala(settings):
    routing = RoutingServiceImpl(settings)
    accion = routing.definir_accion(
        score=0.95,
        tiene_info=True,
        requiere_derivacion=False,
        pregunta="Quiero hablar con un supervisor ahora",
    )
    assert accion == AccionRouter.ESCALAR


def test_score_muy_bajo_escala(settings):
    routing = RoutingServiceImpl(settings)
    accion = routing.definir_accion(
        score=0.15,
        tiene_info=False,
        requiere_derivacion=False,
        pregunta="Pregunta cualquiera",
    )
    assert accion == AccionRouter.ESCALAR


def test_alta_confianza_y_derivacion_requerida_deriva(settings):
    routing = RoutingServiceImpl(settings)
    accion = routing.definir_accion(
        score=0.85,
        tiene_info=True,
        requiere_derivacion=True,
        pregunta="No puedo iniciar sesión desde hace tres días",
    )
    assert accion == AccionRouter.DERIVAR


def test_alta_confianza_sin_derivacion_responde(settings):
    routing = RoutingServiceImpl(settings)
    accion = routing.definir_accion(
        score=0.85,
        tiene_info=True,
        requiere_derivacion=False,
        pregunta="¿Cómo restablezco mi contraseña?",
    )
    assert accion == AccionRouter.RESPONDER


def test_sin_info_aunque_score_medio_escala(settings):
    routing = RoutingServiceImpl(settings)
    accion = routing.definir_accion(
        score=0.50,
        tiene_info=False,
        requiere_derivacion=False,
        pregunta="¿Dónde está mi pedido?",
    )
    assert accion == AccionRouter.ESCALAR
