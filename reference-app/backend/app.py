from flask import Flask, render_template, request, jsonify
import logging

import pymongo
from flask_pymongo import PyMongo

from flask_opentracing import FlaskTracer
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from prometheus_flask_exporter import PrometheusMetrics

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.shim.opentracing_shim import create_tracer
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# jaeger
def tracerConfig():
    config = Config(
           config = {
                'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'local_agent': {
                 'reporting_host': 'simplest-agent.observability.svc.cluster.local',
                 'reporting_port': 6831,
               }
        },
        service_name="service_backend",
        validate=True,
        metrics_factory=PrometheusMetricsFactory(service_name_label="service_backend")
    )
    return config.initialize_tracer()

app = Flask(__name__)
metrics = PrometheusMetrics(app)
metrics.info("app_info", "Application info", version="1.0.3")

logging.getLogger("").handlers = []
logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

jaegerTracer = tracerConfig()
tracing = FlaskTracer(jaegerTracer, True, app)

app.config["MONGO_DBNAME"] = "example-mongodb"
app.config[
    "MONGO_URI"
] = "mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb"

mongo = PyMongo(app)


@app.route("/")
def homepage():
    with jaegerTracer.start_span('Parent Span') as span:
        span.log_kv({'event': 'This is parent span in home page'})
        with jaegerTracer.start_span('Child Span', child_of=span) as child_span:
            child_span.log_kv({'event': 'This is child span in home page'})
    return "Hello World"


@app.route("/api")
def my_api():
    answer = "something"
    return jsonify(repsonse=answer)

@app.route('/findtestrecord')
def index():
    with jaegerTracer.start_span('Requesting Vendor site for record') as span:
        span.log_kv({'event': 'Specified record not found in vendor site'})
    return "Record not found", 400


@app.route("/star", methods=["POST"])
def add_star():
    star = mongo.db.stars
    name = request.json["name"]
    distance = request.json["distance"]
    star_id = star.insert({"name": name, "distance": distance})
    new_star = star.find_one({"_id": star_id})
    output = {"name": new_star["name"], "distance": new_star["distance"]}
    return jsonify({"result": output})


if __name__ == "__main__":
    app.run()
