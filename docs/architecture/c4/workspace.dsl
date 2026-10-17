workspace "AireMisti IoT" "Modelo C4 de la red de monitoreo de calidad del aire de Arequipa (Laboratorio 06)." {

    !identifiers hierarchical

    model {
        ciudadano = person "Ciudadano" "Vecino de Arequipa que consulta la calidad del aire y recibe alertas."
        analista = person "Analista municipal" "Registra sensores, revisa alertas y descarga el histórico."
        airemisti = softwareSystem "AireMisti IoT" "Recibe las lecturas de 40 sensores, publica el mapa de calidad del aire y emite alertas cuando PM10 supera 150 µg/m³."
        sensores_red = softwareSystem "Red de sensores PM10 / PM2.5" "40 sensores con WiFi/4G y microSD que miden cada minuto y guardan lecturas durante los cortes." "Externo"
        telegram = softwareSystem "Telegram Bot API" "Canal público donde se publican las alertas." "Externo"
        osm = softwareSystem "OpenStreetMap" "Servicio de teselas del mapa base." "Externo"

        ciudadano -> airemisti "Consulta el mapa de calidad del aire"
        analista -> airemisti "Registra sensores, revisa alertas y descarga el histórico"
        sensores_red -> airemisti "Envía lecturas de PM10 y PM2.5 cada minuto" "MQTT/TLS"
        airemisti -> telegram "Publica alertas de contaminación" "HTTPS/JSON"
        airemisti -> osm "Obtiene las teselas del mapa" "HTTPS"
        telegram -> ciudadano "Notifica las alertas del canal"
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
