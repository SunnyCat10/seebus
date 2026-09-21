# SeeBus

IoT-assisted adaptive bus scheduling system for collecting bus-station
occupancy estimates and dynamically adjusting bus schedules.

## Components

- `backend` - Java / Spring Boot REST API and scheduling engine
- `frontend` - Web schedule viewer and administration interface
- `firmware` - ESP32 station firmware
- `deploy` - Deployment configuration
- `scripts` - Local development and deployment helper scripts

## Local Development

### 1. Initial setup

After cloning the repository, create your local environment configuration:

```powershell
.\scripts\setup.ps1
```

This creates `.env` from the committed `.env.example`.

The `.env` file is ignored by Git and should contain your local configuration
and development credentials.

Edit `.env` and replace the placeholder values:

```dotenv
SEEBUS_SENSOR_TOKEN=YOUR_LOCAL_SENSOR_TOKEN
SEEBUS_ADMIN_TOKEN=YOUR_LOCAL_ADMIN_TOKEN
SEEBUS_SWAGGER_ENABLED=true
SEEBUS_DEPLOY_HOST=YOUR_DEPLOY_HOST
```

Do not commit `.env`.

### 2. Start the backend

From the repository root:

```powershell
.\scripts\dev.ps1
```

The script loads the local `.env` configuration and starts the Spring Boot
backend.

By default, the backend is available at:

```text
http://localhost:8080
```

The health endpoint can be used to verify that the backend is running:

```text
http://localhost:8080/api/health
```

### 3. API documentation

When the backend is running, open the generated Swagger UI with:

```powershell
.\scripts\api.ps1
```

Swagger UI:

```text
http://localhost:8080/swagger-ui.html
```

OpenAPI JSON:

```text
http://localhost:8080/v3/api-docs
```

API documentation is controlled by:

```dotenv
SEEBUS_SWAGGER_ENABLED=true
```

Swagger and the OpenAPI endpoint are disabled by default when this variable
is not enabled.

## Environment Variables

The following variables are currently used by SeeBus:

| Variable | Description |
| --- | --- |
| `SEEBUS_SENSOR_TOKEN` | Authentication token used by ESP32 sensor devices |
| `SEEBUS_ADMIN_TOKEN` | Authentication token used for administration endpoints |
| `SEEBUS_SWAGGER_ENABLED` | Enables Swagger UI and OpenAPI generation |
| `SEEBUS_DEPLOY_HOST` | Hostname or IP address used by the deployment script |

Local values should be stored in `.env`.

Production secrets should be configured through the production environment
and should not be stored in the repository.

## Deployment

Deploy the current version to the configured SeeBus server with:

```powershell
.\scripts\deploy.ps1
```

The deployment host is taken from:

```dotenv
SEEBUS_DEPLOY_HOST
```

You can also override it for a single deployment:

```powershell
.\scripts\deploy.ps1 -HostName <host>
```

The deployment script connects to the server over SSH and runs:

```bash
cd ~/seebus && ./deploy/deploy.sh
```

The local SSH key is expected at:

```text
~/.ssh/gerbil
```

## Helper Scripts

The repository currently provides:

```text
scripts/
├── setup.ps1      # Creates local .env configuration
├── load-env.ps1   # Loads variables from .env
├── dev.ps1        # Starts the backend for local development
├── api.ps1        # Opens the local Swagger UI
└── deploy.ps1     # Deploys SeeBus to the configured server
```

Run scripts from the repository root, for example:

```powershell
.\scripts\dev.ps1
```

The scripts resolve project directories relative to their own location, so
they can also be invoked from other directories.

## Security

Local credentials belong in `.env`.

The file is ignored by Git.

Only `.env.example` should be committed, and it should contain placeholder
values rather than real credentials.

Swagger/OpenAPI should normally remain disabled in production unless there
is a specific reason to expose it.
