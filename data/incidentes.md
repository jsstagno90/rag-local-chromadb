# Manual técnico de AgendaYa: guía de incidentes

Esta guía explica qué hacer cuando algo falla en producción. Un incidente es cualquier problema que impide reservar, pagar o usar el panel.

## Niveles de severidad

- **SEV1:** nadie puede reservar o pagar. Ejemplo: la API no responde o la base de datos está caída. Se atiende de inmediato, a cualquier hora.
- **SEV2:** una función importante anda mal para una parte de los usuarios. Ejemplo: los webhooks de pago fallan o la búsqueda tarda más de 5 segundos. Se atiende en menos de una hora en horario laboral.
- **SEV3:** un problema menor que tiene una forma de evitarse. Ejemplo: un reporte del panel muestra un número mal. Se resuelve en el próximo ciclo de trabajo.

## Guardia

Hay una persona de guardia por semana, que rota entre los integrantes del equipo de backend. La guardia recibe las alertas de SEV1 por teléfono y las de SEV2 por Slack, en el canal #incidentes.

## Pasos ante un SEV1

1. Confirmar el problema mirando el tablero de monitoreo y haciendo una reserva de prueba.
2. Avisar en #incidentes que hay un SEV1 y quién lo está atendiendo.
3. Revisar si hubo un deploy reciente. Si lo hubo, volver a la versión anterior antes de investigar más: primero se restablece el servicio, después se busca la causa.
4. Publicar una actualización en la página de estado cada 30 minutos mientras dure el incidente.
5. Cuando el servicio vuelve a funcionar, avisar en #incidentes y en la página de estado.

## Problemas frecuentes

**La búsqueda de horarios está lenta.** Casi siempre es Redis. Revisar si Redis responde; si está caído, la API usa PostgreSQL directamente y anda más lenta, pero anda. Reiniciar Redis suele resolverlo.

**Los turnos quedan en `pending_payment` aunque el cliente pagó.** Suele ser un problema con los webhooks de Mercado Pago. Revisar los logs del endpoint `/webhooks/mercadopago`. El proceso programado que corre cada 10 minutos debería corregir los turnos atrasados.

**Error 429 en la API de WhatsApp.** Se superó el límite de mensajes. Los avisos se encolan y se reintentan con backoff exponencial, así que no hace falta hacer nada salvo que dure más de una hora.

## Después del incidente

Todo SEV1 y SEV2 tiene un postmortem dentro de los 3 días hábiles siguientes. El postmortem explica qué pasó, cuál fue la causa, cuánto duró y qué se va a cambiar para que no se repita. No se buscan culpables: se buscan mejoras en el sistema.
