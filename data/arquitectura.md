# Manual técnico de AgendaYa: arquitectura

AgendaYa es una plataforma de turnos online para peluquerías, consultorios y talleres. Los clientes reservan desde una web o desde WhatsApp, y cada negocio administra su agenda desde un panel.

## Componentes principales

El sistema tiene cuatro partes:

- **Frontend web:** una aplicación en React que usan los clientes para reservar y los negocios para ver su agenda. Se publica en Vercel.
- **API:** un backend en FastAPI (Python 3.12) que expone los endpoints de turnos, negocios, clientes y pagos. Corre en dos instancias detrás de un balanceador de carga.
- **Base de datos:** PostgreSQL 16 administrado en Supabase. Cada negocio es un "tenant" y todas las tablas tienen la columna `business_id` para separar los datos.
- **Caché:** Redis guarda la disponibilidad de horarios de cada negocio durante 60 segundos, para no consultar PostgreSQL en cada búsqueda.

## Flujo de una reserva

1. El cliente elige negocio, servicio y horario en el frontend.
2. El frontend consulta la disponibilidad a la API. La API busca primero en Redis y, si no encuentra el dato, lo calcula desde PostgreSQL y lo guarda en Redis.
3. El cliente confirma el turno. La API vuelve a verificar la disponibilidad directamente en PostgreSQL, dentro de una transacción, para evitar que dos personas reserven el mismo horario.
4. Si el servicio requiere seña, la API crea un link de pago de Mercado Pago (ver el manual de pagos).
5. Cuando el turno queda confirmado, se borra de Redis la disponibilidad de ese negocio para que la próxima búsqueda vea el horario ocupado.

## Escalado

La API escala de forma horizontal: se agregan instancias cuando el uso de CPU supera el 70% durante cinco minutos. Como la API no guarda estado en memoria, cualquier instancia puede atender cualquier pedido. Las sesiones de los usuarios se guardan en Redis, no en la instancia.

PostgreSQL usa una réplica de lectura para los reportes del panel de negocios, así las consultas pesadas de estadísticas no afectan a las reservas.

## Qué pasa si se cae Redis

Si Redis no responde, la API sigue funcionando: calcula la disponibilidad directamente desde PostgreSQL. El sistema se vuelve más lento (la latencia de búsqueda sube de unos 80 ms a unos 400 ms), pero no se pierden reservas, porque la confirmación final siempre se valida en PostgreSQL. Las sesiones activas sí se pierden y los usuarios del panel tienen que volver a iniciar sesión.

## Entornos

Hay tres entornos: desarrollo, staging y producción. Cada uno tiene su propia base de datos y su propio Redis. Los cambios pasan primero por staging, donde corren los tests automáticos, y recién después se publican en producción.
