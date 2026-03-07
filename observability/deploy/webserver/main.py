
import os
import socket

import logging

from flask import Flask, jsonify, current_app, g
import mysql.connector


from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# otel tracing libraries
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# otel metrics libraries
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# otel logging libraries 
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor

local_hostname = socket.gethostname()
app = Flask(__name__)

# -----------------------------------------------
# ---------------------- OPENTELEMETRY
# -----------------------------------------------

resource = Resource.create(attributes={
    SERVICE_NAME: "cct-webserver"
})

# ------------- traces configs
tracerProvider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter())
tracerProvider.add_span_processor(processor)
trace.set_tracer_provider(tracerProvider)

# ------------- metrics configs
reader = PeriodicExportingMetricReader(OTLPMetricExporter())
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)

# ------------- logging configs
logger_provider = LoggerProvider(
    resource=Resource.create(
        {
            "service.name": "cct-app",
            "service.instance.id": local_hostname,
        }
    )
)
set_logger_provider(logger_provider)

logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

# Set the root logger level to NOTSET to ensure all messages are captured
logging.getLogger().setLevel(logging.NOTSET)

# Attach OTLP handler to root logger
logging.getLogger().addHandler(handler)

logger = logging.getLogger("cct-app")

# ------------- libraries configs
instrumentor = FlaskInstrumentor()
instrumentor.instrument_app(app, enable_commenter=True, excluded_urls="/health")

MySQLInstrumentor().instrument(enable_commenter=True)

# -----------------------------------------------
# ---------------------- SQL
# -----------------------------------------------

if os.getenv('MYSQL_PASSWORD_FILE') is not None:
    with open(os.getenv('MYSQL_PASSWORD_FILE'), "r") as password_file:
        DB_PASSWORD = password_file.read()
else:
    DB_PASSWORD = os.getenv('MYSQL_PASSWORD')

def get_db_connection():
    if ('db_connection' in g and not g.db_connection.is_connected()) or 'db_connection' not in g:
        logger.debug('Getting new DB connection...')
        g.db_connection = mysql.connector.connect(
            user=os.getenv('MYSQL_USER'), 
            password=DB_PASSWORD,
            host=os.getenv('MYSQL_HOST'),
            database=os.getenv('MYSQL_DATABASE'),
            port=int(os.getenv('MYSQL_PORT'))
        )

    return g.db_connection

# -----------------------------------------------
# ---------------------- FLASK
# -----------------------------------------------

app.config['IS_SERVER_HEALTHY'] = True
logger.info('App is now running...')

@app.route('/make-unhealthy', methods=['GET'])
def make_unhealthy():
    logger.error('App is now unhealthy')
    current_app.config['IS_SERVER_HEALTHY'] = False
    return 'Server is now unhealthy'


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'ok': current_app.config['IS_SERVER_HEALTHY']
    }), (200 if current_app.config['IS_SERVER_HEALTHY'] else 500)


@app.route('/')
def get_data():
    db_connection = get_db_connection()
    with db_connection.cursor() as cur:
        cur.execute('''SELECT * FROM accounts''')
        data = cur.fetchall()

        logger.debug('Data from db has been fetched')

        html = '''
        <html>
            <head>
                <style>
                table, th, td {
                    border: 1px solid black;
                    border-collapse: collapse;
                }
                </style>
            </head>
            <body>
                <table>
                    <tr>
                        <th>Id</th>
                        <th>Name</th>
                        <th>Balance</th>
                    </tr>
        '''
        
        for d in data:
            html += f'''
                        <tr>
                            <td>{d[0]}</td>
                            <td>{d[1]}</td>
                            <td>{d[2]}</td>
                        </tr>
            '''
        html += f'''
                </table>
                <hr />
                <p>Hostname: {local_hostname}</p>
            </body>
        </html>'''
            
        return html


@app.teardown_appcontext
def teardown_db_connection(exception):
    db_connection = g.pop('db_connection', None)

    if db_connection is not None:
        db_connection.close()
        logger.info('Db connection closed')