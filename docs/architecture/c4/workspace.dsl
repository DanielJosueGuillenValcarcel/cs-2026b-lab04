workspace "AireMisti IoT" "Modelo C4 de la red de monitoreo de calidad del aire de Arequipa (Laboratorio 06)." {

    !identifiers hierarchical

    model {
        ciudadano = person "Ciudadano" "Vecino de Arequipa que consulta la calidad del aire y recibe alertas."
        analista = person "Analista municipal" "Registra sensores, revisa alertas y descarga el histórico."
        airemisti = softwareSystem "AireMisti IoT" "Recibe las lecturas de 40 sensores, publica el mapa de calidad del aire y emite alertas cuando PM10 supera 150 µg/m³." {
            mapa_web = container "Mapa web" "Mapa en tiempo real para ciudadanos y panel de administración para el analista." "JavaScript + Leaflet" "Web Browser"
            app = container "Monolito Django" "Monolito modular: API REST, vistas web y proceso de ingesta suscrito al broker." "Python 3.12 / Django + Gunicorn" {
                ingesta = component "Ingesta" "Se suscribe a airemisti/+/lecturas, valida cada lote y lo guarda sin duplicados. Corre como proceso aparte (manage.py ingesta)." "Django app + paho-mqtt"
                sensores = component "Sensores" "Registro, ubicación y ciclo de vida de los sensores (ACTIVO, SIN_SENAL, SINCRONIZANDO, MANTENIMIENTO, BAJA)." "Django app"
                lecturas = component "Lecturas e histórico" "Guarda lecturas por lotes con ON CONFLICT DO NOTHING y exporta el histórico en CSV." "Django app"
                alertas = component "Alertas" "Decide si una lectura supera el umbral y gestiona la alerta vigente por distrito; su tarea evaluar() la ejecuta el Worker." "Django app"
                mapa = component "Mapa público" "API de solo lectura con el nivel de cada sensor y las alertas vigentes." "Django REST Framework"
            }
            worker = container "Worker Celery" "Evalúa el umbral, crea y publica las alertas, y revisa los sensores sin señal (RF-07)." "Python 3.12 / Celery"
            broker = container "Broker MQTT" "Recibe las lecturas de los sensores y las retiene si la ingesta no está disponible." "Eclipse Mosquitto (QoS 1, persistente, TLS)" "Queue"
            db = container "Base de datos" "Sensores, lecturas particionadas por mes y alertas; un esquema por módulo." "PostgreSQL" "Database"
            redis = container "Cola y caché" "Últimas lecturas para el mapa y cola de tareas de Celery." "Redis" "Database"
        }
        sensores_red = softwareSystem "Red de sensores PM10 / PM2.5" "40 sensores con WiFi/4G y microSD que miden cada minuto y guardan lecturas durante los cortes." "Externo"
        telegram = softwareSystem "Telegram Bot API" "Canal público donde se publican las alertas." "Externo"
        osm = softwareSystem "OpenStreetMap" "Servicio de teselas del mapa base." "Externo"

        ciudadano -> airemisti "Consulta el mapa de calidad del aire"
        analista -> airemisti "Registra sensores, revisa alertas y descarga el histórico"
        sensores_red -> airemisti "Envía lecturas de PM10 y PM2.5 cada minuto" "MQTT/TLS"
        airemisti -> telegram "Publica alertas de contaminación" "HTTPS/JSON"
        airemisti -> osm "Obtiene las teselas del mapa" "HTTPS"
        telegram -> ciudadano "Notifica las alertas del canal"

        ciudadano -> airemisti.mapa_web "Consulta el mapa" "HTTPS"
        analista -> airemisti.mapa_web "Administra sensores y descarga el histórico" "HTTPS"
        airemisti.mapa_web -> airemisti.app "Pide niveles, alertas y CSV" "HTTPS/JSON (REST)"
        airemisti.mapa_web -> osm "Carga las teselas" "HTTPS"
        sensores_red -> airemisti.broker "Publica lecturas en su tema (QoS 1)" "MQTT/TLS 8883"
        airemisti.app -> airemisti.broker "Se suscribe a las lecturas (sesión persistente)" "MQTT"
        airemisti.app -> airemisti.db "Lee y escribe" "SQL/TCP"
        airemisti.app -> airemisti.redis "Guarda la última lectura y encola la evaluación de alertas" "Redis protocol"
        airemisti.worker -> airemisti.redis "Consume tareas" "Redis protocol"
        airemisti.worker -> airemisti.db "Lee lecturas y registra alertas" "SQL/TCP"
        airemisti.worker -> telegram "Publica alertas" "HTTPS/JSON"

        airemisti.mapa_web -> airemisti.app.mapa "Consulta niveles y alertas vigentes" "HTTPS/JSON"
        airemisti.mapa_web -> airemisti.app.sensores "Registra y da de baja sensores" "HTTPS/JSON"
        airemisti.mapa_web -> airemisti.app.lecturas "Descarga el histórico" "HTTPS/CSV"
        airemisti.app.ingesta -> airemisti.broker "Recibe lecturas" "MQTT"
        airemisti.app.ingesta -> airemisti.app.sensores "Valida el sensor y actualiza su estado"
        airemisti.app.ingesta -> airemisti.app.lecturas "Guarda el lote sin duplicados"
        airemisti.app.ingesta -> airemisti.app.alertas "Encola evaluar() como tarea Celery"
        airemisti.app.alertas -> airemisti.app.lecturas "Usa la lectura que superó el umbral"
        airemisti.app.mapa -> airemisti.app.sensores "Lee ubicación y estado"
        airemisti.app.mapa -> airemisti.app.lecturas "Lee el histórico reciente"
        airemisti.app.mapa -> airemisti.app.alertas "Lee alertas vigentes"
        airemisti.app.sensores -> airemisti.db "Lee y escribe" "SQL"
        airemisti.app.lecturas -> airemisti.db "Inserta por lotes y consulta" "SQL"
        airemisti.app.alertas -> airemisti.redis "Encola la tarea" "Redis protocol"
        airemisti.app.mapa -> airemisti.redis "Lee las últimas lecturas" "Redis protocol"
    }

    views {
        properties {
            "c4plantuml.tags" "true"
        }

        systemContext airemisti "Contexto" "Nivel 1: AireMisti IoT, sus usuarios y los sistemas externos de los que depende." {
            title "Nivel 1 — Contexto del sistema AireMisti IoT"
            include *
            autolayout lr
        }
        container airemisti "Contenedores" "Nivel 2: contenedores de AireMisti IoT, con su tecnología y protocolos." {
            title "Nivel 2 — Contenedores de AireMisti IoT"
            include *
            autolayout lr
        }
        component airemisti.app "Componentes" "Nivel 3: módulos del Monolito Django (coinciden con paquetes.puml del Lab 05)." {
            title "Nivel 3 — Componentes del Monolito Django"
            include *
            autolayout lr
        }

        styles {
            element "Person" {
                shape person
                background #08427B
                color #ffffff
            }
            element "Software System" {
                background #1168BD
                color #ffffff
            }
            element "Externo" {
                background #999999
                color #ffffff
            }
            element "Container" {
                background #438DD5
                color #ffffff
            }
            element "Component" {
                background #85BBF0
                color #000000
            }
            element "Database" {
                shape cylinder
            }
            element "Queue" {
                shape pipe
            }
            element "Web Browser" {
                shape WebBrowser
            }
            element "Infrastructure Node" {
                background #ffffff
                color #000000
            }
        }
    }
}
