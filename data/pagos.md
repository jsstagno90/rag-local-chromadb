# Manual técnico de AgendaYa: pagos y señas

Los negocios pueden pedir una seña para confirmar un turno. AgendaYa cobra las señas con Mercado Pago y nunca guarda datos de tarjetas.

## Configuración de la seña

Cada servicio tiene un campo `deposit_percent` que indica qué porcentaje del precio se cobra como seña. Puede ir de 0 a 50. Si vale 0, el turno se confirma sin pago. El valor por defecto para servicios nuevos es 0.

## Flujo de cobro

1. Cuando el cliente confirma un turno con seña, la API crea una "preferencia de pago" en Mercado Pago con el monto de la seña.
2. El turno queda en estado `pending_payment` y el horario se reserva durante 15 minutos.
3. El cliente paga en el checkout de Mercado Pago.
4. Mercado Pago avisa el resultado a la API con un webhook en el endpoint `/webhooks/mercadopago`.
5. Si el pago fue aprobado, el turno pasa a `confirmed`. Si en 15 minutos no llega un pago aprobado, el turno se cancela automáticamente y el horario se libera.

## Webhooks

El webhook puede llegar más de una vez para el mismo pago, por eso la API guarda el `payment_id` y procesa cada pago una sola vez. Antes de cambiar el estado del turno, la API consulta el pago directamente a Mercado Pago, para no confiar ciegamente en el contenido del webhook.

Si el endpoint de webhooks falla, Mercado Pago reintenta el aviso durante varias horas. Un proceso programado revisa cada 10 minutos los turnos en `pending_payment` y consulta su estado en Mercado Pago, por si algún webhook se perdió.

## Reembolsos

Si el negocio cancela un turno ya pagado, la seña se devuelve completa y de forma automática. Si el cliente cancela con más de 24 horas de anticipación, también se le devuelve la seña. Si cancela con menos de 24 horas, la seña queda para el negocio, salvo que el negocio decida devolverla desde el panel.

Los reembolsos se piden a Mercado Pago desde la API y pueden tardar hasta 10 días hábiles en verse en la tarjeta del cliente, según el banco.

## Comisiones

AgendaYa no cobra comisión sobre las señas. El negocio paga la comisión de Mercado Pago, que se descuenta del monto que recibe. AgendaYa cobra a cada negocio una suscripción mensual fija según su plan.
