document.addEventListener('DOMContentLoaded', () => {
    // 1. Solicitar permisos al navegador/celular para enviar notificaciones push
    if ("Notification" in window) {
        if (Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }
    }

    // 2. Control para no saturar de notificaciones (ej: avisar solo 1 vez por hora)
    let ultimaAlerta = 0;
    // Cambia este valor para ajustar cada cuánto suena la alarma (en milisegundos)
    // 60000 = 1 minuto (ideal para probar) | 3600000 = 1 hora (ideal para producción)
    const TIEMPO_SILENCIO = 60000; 

    // 3. Función que consulta nuestra API en Flask
    async function chequearEntregas() {
        try {
            const response = await fetch('/api/alertas');
            const data = await response.json();

            if (data.hay_entregas) {
                const ahora = Date.now();
                
                // Solo notifica si ha pasado el tiempo de silencio desde la última alerta
                if (ahora - ultimaAlerta > TIEMPO_SILENCIO) {
                    emitirNotificacion(data.cantidad, data.vehiculos);
                    ultimaAlerta = ahora;
                }
            }
        } catch (error) {
            console.error("Error al consultar alertas:", error);
        }
    }

    // 4. Función que construye y dispara la alerta visual/sonora
    function emitirNotificacion(cantidad, vehiculos) {
        let mensaje = `Tienes ${cantidad} vehículo(s) para devolver hoy al aeropuerto.\n`;
        vehiculos.forEach(v => {
            // Formatear hora de la alerta extrayendo solo HH:MM
            let hora = new Date(v.fecha_hora_entrega).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            mensaje += `\n🚗 ${v.matricula} (Celda ${v.codigo_celda}) - ${hora}`;
        });

        if ("Notification" in window && Notification.permission === "granted") {
            // Notificación nativa (Sale en la barra del celular o esquina de Windows)
            new Notification("¡Entregas Pendientes!", {
                body: mensaje,
                vibrate: [200, 100, 200, 100, 200], // Patrón de vibración para celulares
                requireInteraction: true // Evita que la notificación desaparezca sola en PC
            });
        } else {
            // Respaldo por si el celular tiene bloqueadas las notificaciones push
            alert("⚠️ ALERTA DE ENTREGAS ⚠️\n\n" + mensaje);
        }
    }

    // 5. Motor de ejecución: 
    chequearEntregas(); // Revisa apenas abres la página
    setInterval(chequearEntregas, 60000); // Luego sigue revisando cada 1 minuto (60000 ms)
});
