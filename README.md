# SeeBus

IoT-assisted adaptive bus scheduling system that collects bus-station
occupancy estimates and dynamically adjusts bus schedules.

## Components

- `backend` - Java / Spring Boot API and scheduling engine
- `frontend` - React schedule viewer and admin interface
- `firmware` - ESP32 station firmware
- `deploy` - Deployment configuration
- `scripts` - Development and deployment helpers

## Local Development

Start the complete development environment:

```powershell
.\scripts\dev.ps1
```

This starts:

```text
Backend:     http://localhost:8080
Frontend:    http://localhost:5173
Swagger UI:  http://localhost:8080/swagger-ui.html
```

Local development uses the committed `.env.example` configuration by default.

Press `Ctrl+C` to stop both the frontend and backend.

### Local overrides

To override the default development configuration:

```powershell
Copy-Item .env.example .env
```

Edit `.env`, then run:

```powershell
.\scripts\dev.ps1 -UseEnv
```

`.env.example` is loaded first and values from `.env` override it.

Do not commit `.env`.

## Mock Sensor Readings

Send a reading to the local development server:

```powershell
.\scripts\mock-reading.ps1 `
    -StationId station-1 `
    -Occupancy 0.75 `
    -Dev
```

`-Dev` uses `.env.example`, matching the configuration used by `dev.ps1`.

To use the configuration from `.env` instead:

```powershell
.\scripts\mock-reading.ps1 `
    -StationId station-1 `
    -Occupancy 0.75
```

This can be used to send readings to another SeeBus environment by configuring:

```dotenv
SEEBUS_SENSOR_TOKEN=<sensor-token>
SEEBUS_API_URL=https://<api-host>
```

## Environment Variables

Important variables:

| Variable | Description |
| --- | --- |
| `SEEBUS_SENSOR_TOKEN` | Sensor authentication token |
| `SEEBUS_ADMIN_TOKEN` | Admin authentication token |
| `SEEBUS_SWAGGER_ENABLED` | Enables Swagger/OpenAPI |
| `SEEBUS_API_URL` | SeeBus API URL used by helper scripts |
| `VITE_API_BASE_URL` | API URL used by the frontend |
| `SEEBUS_DEPLOY_HOST` | Deployment server |

`.env.example` contains safe development defaults.

`.env` is ignored by Git and can contain local overrides or private values.

> `VITE_*` variables are visible to frontend code and must not contain secrets.

## API

Health check:

```text
http://localhost:8080/api/health
```

Swagger UI:

```text
http://localhost:8080/swagger-ui.html
```

OpenAPI:

```text
http://localhost:8080/v3/api-docs
```

Swagger can also be opened with:

```powershell
.\scripts\api.ps1
```

## Deployment

Deploy using:

```powershell
.\scripts\deploy.ps1
```

The deployment host is taken from:

```dotenv
SEEBUS_DEPLOY_HOST
```

or can be overridden:

```powershell
.\scripts\deploy.ps1 -HostName <host>
```

## Scripts

```text
scripts/
├── setup.ps1
├── load-env.ps1
├── dev.ps1
├── mock-reading.ps1
├── api.ps1
└── deploy.ps1
```

Typical development workflow:

```powershell
# Start SeeBus
.\scripts\dev.ps1

# In another terminal, send a mock reading
.\scripts\mock-reading.ps1 -StationId station-1 -Occupancy 0.8 -Dev
```