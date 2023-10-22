from flask import Flask, render_template, request, jsonify
import logging

import pymongo
from flask_pymongo import PyMongo

from flask_opentracing import FlaskTracer
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
#from opentelemetry.instrumentation.flask import FlaskInstrumentor
#from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_flask_exporter import PrometheusMetrics

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.shim.opentracing_shim import create_tracer
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# jaeger
#def tracerConfig():
#    config = Config(
#           config = {
#                'sampler': {
#                'type': 'const',
#                'param': 1,
#            },
#            'logging': True,
#            'local_agent': {
#                 'reporting_host': '127.0.0.1',
#                 'reporting_port': 6831,
#                }
#        },
#        service_name="service_backend",
#        validate=True,
#        metrics_factory=PrometheusMetricsFactory(service_name_label="service_backend")
#    )
#    return config.initialize_tracer()

app = Flask(__name__)
#FlaskInstrumentor().instrument_app(app)
#RequestsInstrumentor().instrument()
metrics = PrometheusMetrics(app)
# static information as metric
metrics.info("app_info", "Application info", version="1.0.3")

logging.getLogger("").handlers = []
logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

#jaegerTracer = tracerConfig()
#tracing = FlaskTracer(jaegerTracer, True, app)
trace.set_tracer_provider(
TracerProvider(
        resource=Resource.create({SERVICE_NAME: "service_backend"})
    )
)
#tracer = trace.get_tracer(__name__)
jaeger_exporter = JaegerExporter(
    agent_host_name='jaeger',
    agent_port=6831,
)
#otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
shim = create_tracer(trace)
tracing = FlaskTracer(shim, True, app)

app.config["MONGO_DBNAME"] = "example-mongodb"
app.config[
    "MONGO_URI"
] = "mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb"

mongo = PyMongo(app)


@app.route("/")
def homepage():
    return "Hello World"


@app.route("/api")
def my_api():
    answer = "something"
    return jsonify(repsonse=answer)


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
