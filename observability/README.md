# Observability

Sources:
- [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/)

Observability lets you understand a system from the outside by letting you ask questions about that system without knowing its inner workings. To ask those questions about your system, your application must be properly **instrumented**. That is, the application code must emit signals such as traces, metrics, and logs. An application is properly instrumented when developers don't need to add more instrumentation to troubleshoot an issue, because they have all of the information they need.

## Distributed tracing

Distributed tracing lets you observe requests as they propagate through complex, distributed systems. Distributed tracing improves the visibility of your application or system’s health and lets you debug behavior that is difficult to reproduce locally. There are 3 concepts involved:

- **Logs** - A log is a timestamped message emitted by services or other components. Unlike traces, they aren’t necessarily associated with any particular user request or transaction. They become far more useful when they are included as part of a span, or when they are correlated with a trace and a span.
- **Spans** - A span represents a single unit of work or operation. Spans track specific operations that a request makes, painting a picture of what happened during the time in which that operation was executed. A span contains name, time-related data, structured log messages, and other metadata (that is, Attributes) to provide information about the operation it tracks.
- **Traces** - A distributed trace, more commonly known as a trace, records the path taken by a single request (made by an application or end user) as it propagates through multiple services in an architecture, such as microservice or serverless applications. A trace is made of one or more spans. The first span represents the root span. Traces can be sampled: if the large majority of your requests are successful and finish with acceptable latency and no errors, you do not need 100% of your traces to meaningfully observe your applications and systems. You just need the right [**sampling**](https://opentelemetry.io/docs/concepts/sampling/).

For example, when a user loads a web page, the initial HTTP request may pass through an API gateway, a backend service, and a database. Each of these steps is represented by a span, and together they form a single trace that shows the end-to-end journey of the request.

## Context Propagation

With context propagation, **signals** (traces, metrics, and logs) can be correlated with each other, regardless of where they are generated. Although not limited to tracing, context propagation allows traces to build causal information about a system across services that are arbitrarily distributed across process and network boundaries.

**Context is an object that contains the information for the sending and receiving service, or execution unit, to correlate one signal with another.**

When Service A calls Service B, Service A includes a trace ID and a span ID as part of the context. Service B uses these values to create a new span that belongs to the same trace, setting the span from Service A as its parent. This makes it possible to track the full flow of a request across service boundaries.

Propagation is the mechanism that moves context between services and processes. It serializes or deserializes the context object and provides the relevant information to be propagated from one service to another.

### Example

A service called Frontend that provides different HTTP endpoints such as `POST /cart/add` and `GET /checkout/` reaches out to a downstream service Product Catalog via an HTTP endpoint `GET /product` to receive details on products that a user wants to add to the cart or that are part of the checkout. To understand activities in the Product Catalog service within the context of requests coming from Frontend, the context (here: Trace ID and Span ID as "Parent ID") is propagated using the `traceparent` header as it is defined in the W3C TraceContext specification. This means the IDs are embedded in the fields of the header:

```
<version>-<trace-id>-<parent-id>-<trace-flags>
```

For example:

```
00-a0892f3577b34da6a3ce929d0e0e4736-f03067aa0ba902b7-01
```

![Traces example](https://opentelemetry.io/docs/concepts/context-propagation/context-propagation-example.svg)

OpenTelemetry SDKs are able to automatically correlate logs with traces. This means they can inject context (Trace ID, Span ID) into a log record. This not only enables you to see logs in the context of the trace and span they belong to, but it also enables you to see logs that belong together across service or execution unit boundaries.

In the case of metrics, context propagation enables you to aggregate measurements in that context. For example, instead of only looking at the response time of all the GET /product requests, you can also get metrics for combinations of `POST /cart/add > GET /product` and `GET /checkout < GET /product`.

---

## Metrics

A metric is a measurement of a service captured at runtime. The moment of capturing a measurement is known as a metric event, which consists not only of the measurement itself, but also the time at which it was captured and associated metadata.

Application and request metrics are important indicators of availability and performance. To understand how metrics in OpenTelemetry works, let's look at a list of components that will play a part in instrumenting our code:

- **Meter Provider** - is a factory for Meters. In most applications, a Meter Provider is initialized once and its lifecycle matches the application’s lifecycle. Meter Provider initialization also includes Resource and Exporter initialization. It is typically the first step in metering with OpenTelemetry.
- **Meter** - A Meter creates metric instruments, capturing measurements about a service at runtime. Meters are created from Meter Providers.
- **Metric Exporter** - Metric Exporters send metric data to a consumer. This consumer can be standard output for debugging during development, the OpenTelemetry Collector, or any open source or vendor backend of your choice.
- **Metric Instruments** - measurements are captured by metric instruments. A metric instrument is defined by:
    - Name
    - Kind - `Counter`, `UpDownCounter`, `Gauge`, `Histogram`
    - Unit (optional)
    - Description (optional)
    
    The name, unit, and description are chosen by the developer or defined via semantic conventions for common ones like request and process metrics.
- **Aggregation** - An aggregation is a technique whereby a large number of measurements are combined into either exact or estimated statistics about metric events that took place during a time window. The OTLP protocol transports such aggregated metrics. The OpenTelemetry API provides a default aggregation for each instrument which can be overridden using the Views, through which you can customize which metric instruments are to be processed or ignored. You can also customize aggregation and what attributes you want to report on metrics.

## Baggage

Baggage is contextual information that resides next to context. Baggage is a key-value store, which means it lets you propagate any data you like alongside context.

For example, imagine you have a `clientId` at the start of a request, but you'd like for that ID to be available on all spans in a trace, some metrics in another service, and some logs along the way. Because the trace may span multiple services, you need some way to propagate that data without copying the `clientId` across many places in your codebase. By using Context Propagation to pass baggage across these services, the `clientId` is available to add to any additional spans, metrics, or logs.

![Baggage propagation](https://opentelemetry.io/docs/concepts/signals/otel-baggage.svg)

Propagating this information using baggage allows for deeper analysis of telemetry in a backend. For example, if you include information like a User ID on a span that tracks a database call, you can much more easily answer questions like *"which users are experiencing the slowest database calls?"*

---

# Instrumentation

For a system to be observable, it must be instrumented: that is, code from the system’s components must emit signals, such as traces, metrics, and logs.

Using OpenTelemetry, you can instrument your code in two primary ways:

- **Code-based** solutions via official APIs and SDKs for most languages
- **Zero-code** solutions

## Zero-Code instrumentation

Zero-code instrumentation adds the OpenTelemetry API and SDK capabilities to your application typically as an agent or agent-like installation. The specific mechanisms involved may differ by language, ranging from bytecode manipulation, monkey patching, or eBPF to inject calls to the OpenTelemetry API and SDK into your application.

Typically, zero-code instrumentation adds instrumentation for the libraries you’re using. This means that requests and responses, database calls, message queue calls, and so forth are what are instrumented. Your application’s code, however, is not typically instrumented. To instrument your code, you’ll need to use code-based instrumentation.

### Instrumentation Libraries

OpenTelemetry provides instrumentation libraries for many libraries, which is typically done through library hooks or monkey-patching library code.

Native library instrumentation with OpenTelemetry provides better observability and developer experience for users, removing the need for libraries to expose and document hooks.

# Framework Components

## Resources

A resource represents the entity producing telemetry as resource attributes. For example, a process producing telemetry that is running in a container on Kubernetes has a process name, a pod name, a namespace, and possibly a deployment name. All four of these attributes can be included in the resource.

In your observability backend, you can use resource information to better investigate interesting behavior. For example, if your trace or metrics data indicate latency in your system, you can narrow it down to a specific container, pod, or Kubernetes deployment.

![Resource in Jaeger](https://opentelemetry.io/docs/concepts/resources/screenshot-jaeger-resources.png)

## Collector

The OpenTelemetry Collector is a vendor-agnostic proxy that can receive, process, and export telemetry data. It supports receiving telemetry data in multiple formats (for example, OTLP, Jaeger, Prometheus, as well as many commercial/proprietary tools) and sending data to one or more backends. It also supports processing and filtering telemetry data before it gets exported.

![Collector](https://opentelemetry.io/docs/collector/img/otel-collector.svg)

See below for additional info.

---

# [Python Instrumentation](https://opentelemetry.io/docs/zero-code/python/)

Automatic instrumentation with Python uses a Python **agent** that can be attached to any Python application. This agent primarily uses **monkey patching** to modify library functions at runtime, allowing for the capture of telemetry data from many popular libraries and frameworks.

Run the following commands to install the appropriate packages.

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install
```

#### Example of Manually instrumented server

```python
@app.route("/server_request")
def server_request():
    with tracer.start_as_current_span(
        "server_request",
        context=extract(request.headers),
        kind=trace.SpanKind.SERVER,
        attributes=collect_request_attributes(request.environ),
    ):
        print(request.args.get("param"))
        return "served"
```

#### Example of Automatically instrumented server

```python
@app.route("/server_request")
def server_request():
    print(request.args.get("param"))
    return "served"
```

No additional code is required because the agent automatically send telemetry signals.

#### Example of Programmatically instrumented server

```python
instrumentor = FlaskInstrumentor()

app = Flask(__name__)

instrumentor.instrument_app(app)
# instrumentor.instrument_app(app, excluded_urls="/server_request")
@app.route("/server_request")
def server_request():
    print(request.args.get("param"))
    return "served"
```

Programmatic instrumentation is a kind of instrumentation that requires minimal instrumentation code to be added to the application. Only some instrumentation libraries offer additional capabilities that give you greater control over the instrumentation process when used programmatically.

## Application Execution

When the manual instrumentation is used and the server is executed with `python server_manual.py`, the application generates the spans in JSON format and prints them to stdout:

```json
{
  "name": "server_request",
  "context": {
    "trace_id": "0xfa002aad260b5f7110db674a9ddfcd23",
    "span_id": "0x8b8bbaf3ca9c5131",
    "trace_state": "{}"
  },
  "kind": "SpanKind.SERVER",
  "parent_id": null,
  "start_time": "2020-04-30T17:28:57.886397Z",
  "end_time": "2020-04-30T17:28:57.886490Z",
  "status": {
    "status_code": "OK"
  },
  "attributes": {
    "http.method": "GET",
    "http.server_name": "127.0.0.1",
    "http.scheme": "http",
    "host.port": 8082,
    "http.host": "localhost:8082",
    "http.target": "/server_request?param=testing",
    "net.peer.ip": "127.0.0.1",
    "net.peer.port": 52872,
    "http.flavor": "1.1"
  },
  "events": [],
  "links": [],
  "resource": {
    "telemetry.sdk.language": "python",
    "telemetry.sdk.name": "opentelemetry",
    "telemetry.sdk.version": "0.16b1"
  }
}
```

Instead, to run the server with automatic instrumentation:

```bash
opentelemetry-instrument --traces_exporter console --metrics_exporter none --logs_exporter none python server_automatic.py
```

The server code does not contain opentelemetry command because the instrumentation is provided by the `opentelemetry-instrument` agent. The traces are exported to the console and are identical to the one generated by the manually instrumented server.

It is also possible to use the instrumentation libraries (such as `opentelemetry-instrumentation-flask`) by themselves which may have an advantage of customizing options. However, by choosing to do this it means you forego using auto-instrumentation by starting your application with opentelemetry-instrument as this is mutually exclusive.

Some instrumentation libraries include features that allow for more precise control while instrumenting programmatically, the instrumentation library for Flask is one of them: you can exclude URLs from the tracing process:

```python
# instrumentor.instrument_app(app)
instrumentor.instrument_app(app, excluded_urls="/server_request")
```

### Logging

Unlike Traces and Metrics, there is no equivalent Logs API. There is only an SDK. For Python, you use the Python `logger` library, and then the OTel SDK attaches an OTLP handler to the root logger, turning the Python logger into an OTLP logger. Another way this is accomplished is through Python's support for auto-instrumentation of logs.

[Example of automatic logging in Python where log events are associated to a SpanId](https://opentelemetry.io/docs/zero-code/python/logs-example/)

---

## [Collector](https://opentelemetry.io/docs/collector/)

The OpenTelemetry Collector receives traces, metrics, and logs, processes the telemetry, and exports it to a wide variety of observability backends using its components.

It can be deployed as a Docker container:

```bash
docker pull otel/opentelemetry-collector:0.146.1
docker run \
    -p 127.0.0.1:4317:4317 \
    -p 127.0.0.1:4318:4318 \
    -p 127.0.0.1:55679:55679 \
    otel/opentelemetry-collector:0.146.1 \
    2>&1 | tee collector-output.txt # Optionally tee output for easier search later
```

### Deployment

Two pattern are available for the deployment of a collector:

- **Agent pattern** - In the agent deployment pattern, telemetry signals can come from
  - Applications instrumented with an OpenTelemetry SDK using the OpenTelemetry Protocol (OTLP).
  - Collectors using the OTLP exporter.

  The signals are sent to a Collector instance that runs alongside the application or on the same host, such as a sidecar or DaemonSet.
- **Gateway pattern** - The gateway Collector deployment pattern consists of applications or other Collectors sending telemetry signals to a single OTLP endpoint. This endpoint is provided by one or more Collector instances running as a standalone service, for example, in a Kubernetes deployment. Typically, an endpoint is provided per cluster, per data center, or per region. you can use an out-of-the-box load balancer to distribute the load among the Collectors.

### Configuration

The structure of any Collector configuration file (`/etc/<otel-directory>/config.yaml`) consists of four classes of pipeline components that access telemetry data. The config folder depends on the [OTEL distributions](https://opentelemetry.io/docs/collector/distributions/).

- **[Receivers](https://opentelemetry.io/docs/collector/components/receiver/)** - Receivers collect telemetry from one or more sources. They can be pull or push based, and may support one or more data sources.
- **[Processors](https://opentelemetry.io/docs/collector/components/processor/)** - Processors take the data collected by receivers and modify or transform it before sending it to the exporters. Data processing happens according to rules or settings defined for each processor, which might include filtering, dropping, renaming, or recalculating telemetry, among other operations.
- **[Exporters](https://opentelemetry.io/docs/collector/components/exporter/)** - Exporters send data to one or more backends or destinations. Exporters can be pull or push based, and may support one or more data sources. Each key within the `exporters` section defines an exporter instance, The key follows the `type/name` format, where type specifies the exporter type (e.g., `otlp`, `kafka`, `prometheus`), and `name` (optional) can be appended to provide a unique name for multiple instance of the same type.
- **[Connectors](https://opentelemetry.io/docs/collector/components/connector/)** - Connectors join two pipelines, acting as both exporter and receiver. A connector consumes data as an exporter at the end of one pipeline and emits data as a receiver at the beginning of another pipeline. The data consumed and emitted may be of the same type or of different data types. You can use connectors to summarize consumed data, replicate it, or route it. You can configure one or more connectors using the `connectors` section of the Collector configuration file.

After each pipeline component is configured you must enable it using the pipelines within the service section of the configuration file.

Besides pipeline components you can also configure **[extensions](https://opentelemetry.io/docs/collector/components/extension/)**, which expand the capabilities of the Collector to accomplish tasks not directly involved with processing telemetry data. For example, you can add extensions for Collector health monitoring, service discovery, or data forwarding, among others.

**Example**

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  otlp_grpc:
    endpoint: otelcol:4317
    sending_queue:
      batch:

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1777
  zpages:
    endpoint: 0.0.0.0:55679

service:
  extensions: [health_check, pprof, zpages]
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp_grpc]
    metrics:
      receivers: [otlp]
      exporters: [otlp_grpc]
    logs:
      receivers: [otlp]
      exporters: [otlp_grpc]
```

The `service` section is used to configure what components are enabled in the Collector based on the configuration found in the receivers, processors, exporters, and extensions sections. If a component is configured, but not defined within the service section, then it's not enabled.

The service section consists of three subsections:

- **Extensions** - Extensions to be enabled
- **Pipelines** - is where the pipelines are configured, which can be of the types `traces`, `metrics`, and `logs`. A pipeline consists of a set of receivers, processors and exporters.
- **Telemetry** - The `telemetry` config section is where you can set up observability for the Collector itself. It consists of two subsections: logs and metrics.