workspace "AireMisti IoT" "Modelo C4 de la red de monitoreo de calidad del aire de Arequipa (Laboratorio 06, actualizado en el Laboratorio 08 para 400 sensores)." {

    !identifiers hierarchical

    model {
        ciudadano = person "Ciudadano" "Vecino de Arequipa que consulta la calidad del aire y recibe alertas."
        analista = person "Analista municipal" "Registra sensores, revisa alertas y descarga el histórico."
        airemisti = softwareSystem "AireMisti IoT" "Recibe las lecturas de 400 sensores, publica el mapa de calidad del aire y emite alertas cuando PM10 supera 150 µg/m³." {
            mapa_web = container "Mapa web" "Mapa en tiempo real para ciudadanos y panel de administración para el analista. [QA-07]" "JavaScript + Leaflet" "Web Browser"
            app = container "Monolito Django" "Monolito modular: API REST, vistas web y proceso de ingesta suscrito al broker. La ingesta separa los picos frescos de los del backlog y confirma cada lote guardado. [QA-01, QA-02, QA-05]" "Python 3.12 / Django + Gunicorn" {
                ingesta = component "Ingesta" "Se suscribe a airemisti/+/lecturas, guarda cada lote sin duplicados, publica el acuse airemisti/<sensor>/ack y envía solo los picos frescos a la cola alertas. Corre como proceso aparte (manage.py ingesta). [QA-01, QA-02, QA-05]" "Django app + paho-mqtt"
                sensores = component "Sensores" "Registro, ubicación y ciclo de vida de los sensores (ACTIVO, SIN_SENAL, SINCRONIZANDO, MANTENIMIENTO, BAJA)." "Django app"
                lecturas = component "Lecturas e histórico" "Guarda lecturas por lotes con ON CONFLICT DO NOTHING y exporta el histórico en CSV." "Django app"
                alertas = component "Alertas" "Decide si una lectura supera el umbral y gestiona la alerta vigente por distrito; su tarea evaluar() la ejecuta el Worker de alertas. [QA-02]" "Django app"
                mapa = component "Mapa público" "API de solo lectura con el nivel de cada sensor y las alertas vigentes." "Django REST Framework"
            }
            worker_alertas = container "Worker de alertas" "Consume solo la cola alertas (picos frescos): evalúa el umbral y publica la alerta. [QA-02]" "Python 3.12 / Celery (cola alertas)"
            worker = container "Worker histórico" "Consume la cola historico: avisa al analista de los picos del backlog y revisa los sensores sin señal (RF-07). [QA-02]" "Python 3.12 / Celery (cola historico)"
            broker = container "Broker MQTT" "Recibe las lecturas, las retiene hasta 8 h si la ingesta no está disponible y solo deja publicar a cada sensor en su propio tema. [QA-03, QA-04, QA-06, QA-08]" "Eclipse Mosquitto 2.0 (QoS 1, cola de 200 000, autosave 60 s, ACL por patrón, TLS)" "Queue"
            db = container "Base de datos" "Sensores, lecturas particionadas por mes con clave única (sensor, hora) y alertas; un esquema por módulo. [QA-01, QA-05]" "PostgreSQL 16" "Database"
            redis = container "Cola y caché" "Últimas lecturas para el mapa y dos colas de Celery: alertas e historico. [QA-02, QA-07]" "Redis" "Database"
        }
        sensores_red = softwareSystem "Red de sensores PM10 / PM2.5" "400 sensores con WiFi/4G y microSD que miden cada minuto y conservan toda lectura no confirmada hasta recibir el acuse. [QA-01]" "Externo"
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
        airemisti.app -> airemisti.broker "Publica el acuse de cada lote guardado" "MQTT"
        airemisti.broker -> sensores_red "Entrega el acuse al sensor" "MQTT/TLS 8883"
        airemisti.app -> airemisti.redis "Guarda la última lectura y encola los picos en alertas o historico" "Redis protocol"
        airemisti.worker_alertas -> airemisti.redis "Consume la cola alertas" "Redis protocol"
        airemisti.worker_alertas -> airemisti.db "Registra la alerta del distrito" "SQL/TCP"
        airemisti.worker_alertas -> telegram "Publica alertas" "HTTPS/JSON"
        airemisti.worker -> airemisti.redis "Consume la cola historico" "Redis protocol"
        airemisti.worker -> airemisti.db "Lee lecturas y estados de los sensores" "SQL/TCP"

        airemisti.mapa_web -> airemisti.app.mapa "Consulta niveles y alertas vigentes" "HTTPS/JSON"
        airemisti.mapa_web -> airemisti.app.sensores "Registra y da de baja sensores" "HTTPS/JSON"
        airemisti.mapa_web -> airemisti.app.lecturas "Descarga el histórico" "HTTPS/CSV"
        airemisti.app.ingesta -> airemisti.broker "Recibe lecturas y publica acuses" "MQTT"
        airemisti.app.ingesta -> airemisti.app.sensores "Valida el sensor y actualiza su estado"
        airemisti.app.ingesta -> airemisti.app.lecturas "Guarda el lote sin duplicados"
        airemisti.app.ingesta -> airemisti.app.alertas "Encola evaluar() en la cola alertas (solo picos frescos)"
        airemisti.app.alertas -> airemisti.app.lecturas "Usa la lectura que superó el umbral"
        airemisti.app.mapa -> airemisti.app.sensores "Lee ubicación y estado"
        airemisti.app.mapa -> airemisti.app.lecturas "Lee el histórico reciente"
        airemisti.app.mapa -> airemisti.app.alertas "Lee alertas vigentes"
        airemisti.app.sensores -> airemisti.db "Lee y escribe" "SQL"
        airemisti.app.lecturas -> airemisti.db "Inserta por lotes y consulta" "SQL"
        airemisti.app.alertas -> airemisti.redis "Encola la tarea" "Redis protocol"
        airemisti.app.mapa -> airemisti.redis "Lee las últimas lecturas" "Redis protocol"

        produccion = deploymentEnvironment "Producción" {
            deploymentNode "Sensor de calidad del aire (x400)" "Mide PM10 y PM2.5 cada minuto." "Microcontrolador con WiFi/4G y microSD" 400 {
                softwareSystemInstance sensores_red
            }
            deploymentNode "Dispositivo del usuario" "" "Celular o PC con navegador web" {
                containerInstance airemisti.mapa_web
            }
            deploymentNode "VPS en la nube" "Único servidor del MVP (R-03)." "Ubuntu 24.04 LTS, 4 vCPU / 8 GB RAM" {
                nginx = infrastructureNode "Nginx" "Proxy inverso y terminación TLS." "Nginx"
                monitoreo = infrastructureNode "Prometheus + Grafana" "Métricas y tableros de monitoreo." "Prometheus / Grafana"
                python = deploymentNode "Entorno Python" "" "Python 3.12 (virtualenv), servicios systemd" {
                    gunicorn = deploymentNode "Gunicorn" "Sirve la API y ejecuta el proceso de ingesta." "Gunicorn WSGI" {
                        app_inst = containerInstance airemisti.app
                    }
                    deploymentNode "Celery" "" "Dos workers: -Q alertas y -Q historico, + beat" {
                        containerInstance airemisti.worker_alertas
                        containerInstance airemisti.worker
                    }
                }
                deploymentNode "Mosquitto" "" "Servicio systemd, puerto 8883" {
                    containerInstance airemisti.broker
                }
                deploymentNode "PostgreSQL" "" "Servicio systemd, puerto 5432 local" {
                    containerInstance airemisti.db
                }
                deploymentNode "Redis" "" "Servicio systemd, puerto 6379 local" {
                    containerInstance airemisti.redis
                }
                nginx -> python.gunicorn.app_inst "Reenvía las peticiones HTTPS" "HTTP (proxy inverso)"
                monitoreo -> python.gunicorn.app_inst "Recoge métricas" "HTTP /metrics"
            }
        }
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
        container airemisti "Contenedores" "Nivel 2: contenedores de AireMisti IoT, con su tecnología, protocolos y el escenario de calidad que atiende cada uno (Lab 08)." {
            title "Nivel 2 — Contenedores de AireMisti IoT (400 sensores, Lab 08)"
            include *
            autolayout lr
        }
        component airemisti.app "Componentes" "Nivel 3: módulos del Monolito Django (coinciden con paquetes.puml del Lab 05)." {
            title "Nivel 3 — Componentes del Monolito Django"
            include *
            autolayout lr
        }
        dynamic airemisti "IngestaYAlerta" "Dinámico: ingesta de una lectura con PM10 = 180 µg/m³ y emisión de la alerta (HU-03)." {
            title "Vista dinámica — Ingesta de una lectura y emisión de alerta"
            sensores_red -> airemisti.broker "Publica la lectura con QoS 1"
            airemisti.app -> airemisti.broker "Consume la lectura de su suscripción"
            airemisti.app -> airemisti.db "Guarda el lote con ON CONFLICT DO NOTHING"
            airemisti.app -> airemisti.broker "Publica el acuse del lote"
            airemisti.app -> airemisti.redis "Actualiza la última lectura y encola evaluar() en la cola alertas"
            airemisti.worker_alertas -> airemisti.redis "Toma la tarea de la cola alertas"
            airemisti.worker_alertas -> airemisti.db "Registra la alerta del distrito"
            airemisti.worker_alertas -> telegram "Publica la alerta"
            telegram -> ciudadano "Notifica a los suscriptores del canal"
            autolayout lr
        }
        deployment airemisti produccion "Despliegue" "Despliegue del MVP en producción: un VPS, los sensores en campo y el navegador del usuario." {
            title "Vista de despliegue — Producción (MVP)"
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
