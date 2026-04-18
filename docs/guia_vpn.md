# Guía de Configuración de VPN

## Requisitos Previos
- Tener una cuenta activa en el directorio corporativo.
- Contar con la aplicación FortiClient instalada (versión 7.0 o superior).
- Conexión a internet estable.

## Pasos para Configurar la VPN

### Windows
1. Descargar FortiClient desde el portal interno: https://portal.empresa.com/vpn
2. Instalar el programa con permisos de administrador.
3. Abrir FortiClient y seleccionar "Remote Access".
4. Configurar una nueva conexión con los siguientes datos:
   - Nombre: VPN Corporativa
   - Servidor: vpn.empresa.com
   - Puerto: 443
5. Ingresar usuario y contraseña corporativos.
6. Activar la verificación en dos pasos con la app Microsoft Authenticator.
7. Hacer clic en "Conectar".

### macOS
1. Descargar FortiClient desde la App Store o el portal interno.
2. Seguir los mismos pasos de configuración que en Windows.
3. En caso de error de certificado, ir a Preferencias del Sistema > Seguridad y permitir la extensión.

## Problemas Frecuentes

### Error "Credenciales inválidas"
- Verificar que el usuario sea el correo corporativo completo (nombre@empresa.com).
- Asegurarse de que la contraseña no haya expirado.
- Si la cuenta está bloqueada, contactar a soporte Nivel 1.

### Conexión lenta o intermitente
- Verificar la velocidad de internet (mínimo 10 Mbps recomendado).
- Desactivar otros programas que consuman ancho de banda.
- Probar cambiando el servidor a vpn2.empresa.com.

### No se puede acceder a recursos internos
- Confirmar que la VPN esté conectada (ícono verde en la barra de tareas).
- Intentar acceder por IP directa en lugar de nombre de dominio.
- Si persiste, reportar un ticket indicando los recursos inaccesibles.
