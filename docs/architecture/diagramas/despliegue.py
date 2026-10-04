from diagrams import Diagram, Cluster, Edge
from diagrams.aws.iot import IotSensor, IotMqtt
from diagrams.onprem.client import Users
from diagrams.onprem.network import Nginx, Internet
from diagrams.programming.framework import Django
from diagrams.onprem.queue import Celery
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.saas.chat import Telegram

graph_attr = {"fontsize": "20", "bgcolor": "white", "pad": "0.3"}

with Diagram("AireMisti IoT - Vista de despliegue", filename="img/despliegue", show=False,
             direction="LR", graph_attr=graph_attr, outformat="png"):
    sensores = IotSensor("40 sensores\nPM10 / PM2.5\n(microSD local)")
    usuarios = Users("Ciudadanos y\nanalistas")
    with Cluster("Servidor en la nube (VPS 4 vCPU / 8 GB)"):
        broker = IotMqtt("Mosquitto\n(MQTT TLS 8883,\nQoS 1)")
        proxy = Nginx("Nginx\n(HTTPS)")
        with Cluster("Monolito modular"):
            ingesta = Django("Proceso de ingesta\n(suscriptor MQTT)")
            app = Django("Django + Gunicorn\n(API y mapa)")
            worker = Celery("Worker Celery\n(alertas)")
        cache = Redis("Redis\n(últimas lecturas + cola)")
        db = PostgreSQL("PostgreSQL\n(particionado por mes)")
        with Cluster("Monitoreo"):
            prom = Prometheus("Prometheus")
            graf = Grafana("Grafana")
    telegram = Telegram("Canal de alertas\n(Telegram)")
    osm = Internet("OpenStreetMap\n(teselas)")
    sensores >> Edge(label="publica cada minuto") >> broker >> Edge(label="suscripción") >> ingesta
    ingesta >> Edge(label="INSERT por lotes") >> db
    ingesta >> Edge(label="última lectura / encola alerta") >> cache
    cache >> Edge(label="consume tareas") >> worker
    worker >> Edge(label="PM10 > 150", style="dashed") >> telegram
    usuarios >> Edge(label="HTTPS") >> proxy >> app
    app >> Edge(label="lee mapa") >> cache
    app >> Edge(label="histórico") >> db
    app >> Edge(style="dotted") >> osm
    app >> Edge(label="métricas", style="dotted") >> prom >> graf
