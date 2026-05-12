graph TB
%% === STYLES ===
classDef core fill:#1E90FF,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef db fill:#9ACD32,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef external fill:#FFD700,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef worker fill:#DA70D6,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;

%% === USERS ===
User(("Frontend User<br/>Web Interface"))

%% === DATA INGESTION LAYER ===
subgraph "Data Ingestion Layer"
  IngestService["Python Ingest Service<br/>Collects tick data"]:::core
end

%% === MESSAGE BROKER ===
subgraph "Message Broker"
  Redis["Redis<br/>In-memory Message Broker"]:::db
end

%% === WEBSOCKET STREAMING SERVER ===
subgraph "WebSocket Streaming Server"
  WSService["Rust WebSocket Server<br/>Streams tick data"]:::core
end

%% === DATA PROCESSING AND STORAGE ===
subgraph "Data Processing and Storage"
  TaskService["Python Task Service<br/>Aggregates tick data"]:::core
  InfluxDB["InfluxDB<br/>Time-series Database"]:::db
end

%% === TASK SCHEDULING ===
subgraph "Task Scheduling"
  CeleryService["Celery<br/>Task Scheduler"]:::core
end

%% === FRONTEND WEB INTERFACE ===
subgraph "Frontend Web Interface"
  Frontend["Frontend HTML Page<br/>Visualizes candlestick data"]:::core
end

%% === WEB SERVER ===
subgraph "Web Server"
  Nginx["Nginx<br/>Serves static files and proxies WebSocket"]:::core
end

%% === DATA FLOW ===
User -->|"WebSocket connection"| Nginx
Nginx -->|"proxies WebSocket"| WSService
IngestService -->|"tick data"| Redis
Redis -->|"latest tick data"| WSService
WSService -->|"streams tick data"| User
CeleryService -->|"scheduled tasks"| TaskService
TaskService -->|"aggregates tick data"| Redis
TaskService -->|"stores OHLC data"| InfluxDB
Frontend -->|"receives tick data"| WSService
Frontend -->|"visualizes data"| InfluxDB
InfluxDB -->|"historical data"| Grafana

%% === EXTERNAL DEPENDENCIES ===
subgraph "External Dependencies"
  ShioajiAPI["Shioaji API<br/>Financial Data Source"]:::external
end

IngestService -->|"collects data"| ShioajiAPI

%% === GRAFANA ===
subgraph "Visualization"
  Grafana["Grafana<br/>Dashboards for data visualization"]:::core
end

Grafana -->|"visualizes OHLC data"| InfluxDB