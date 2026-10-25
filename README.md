# SeeBus

**SeeBus** is a proof-of-concept system for adaptive public-transport scheduling. Smart bus stations estimate passenger occupancy, a central backend processes readings and calculates upcoming arrivals, and a web app displays the schedule and provides an administration interface.

The project also includes a **separate Python simulator** for comparing scheduling policies under different passenger-demand scenarios.

## System overview

```text
ESP32 station (hardware/) ── readings ──> Spring Boot API (backend/)
                                               │
                                  scheduling and configuration
                                               │
                                               ▼
                                      React app (frontend/)
                                      arrival board + admin

Python simulator (simulation/) ── offline policy experiments and reports
```

## Repository structure

| Directory | What it contains |
| --- | --- |
| [`frontend/`](frontend/) | React, TypeScript, and Chakra UI application: public arrival board and admin dashboard. |
| [`backend/`](backend/) | Java / Spring Boot REST API, station and bus management, readings, authentication, and scheduling policies. |
| [`hardware/`](hardware/) | ESP32 firmware for the ultrasonic station prototype; sends occupancy readings to the backend. |
| [`simulation/`](simulation/) | Standalone Python simulator for comparing scheduling strategies and generating experiment reports. |
| [`deploy/`](deploy/) | Docker Compose configuration for deploying the backend. |
| [`scripts/`](scripts/) | PowerShell tools for development, testing, and deployment. |
| [`documentation/`](documentation/) | Detailed user and programmer documentation for the software, hardware, and simulation. |

## Run the web application locally

**Requirements:** Java 21, Node.js/npm, and PowerShell.

From the repository root:

```powershell
cd frontend
npm ci
cd ..
.\scripts\dev.ps1
```

The script starts the backend and frontend with the development settings in `.env.example`:

- **Web app:** http://localhost:5173
- **Backend API:** http://localhost:8080
- **Swagger UI:** http://localhost:8080/swagger-ui.html

To use local environment overrides, create `.env` from `.env.example` and run `.\scripts\dev.ps1 -UseEnv`. Do not commit `.env` or other credentials.

To test incoming readings without the physical station:

```powershell
.\scripts\mock-reading.ps1 -StationId station-1 -Occupancy 0.75 -Dev
```

## Deployment

- **Backend:** Docker Compose (`deploy/docker-compose.yml`) on a server, with an HTTPS proxy/tunnel in front of the API.
- **Frontend:** Cloudflare Workers using `frontend/wrangler.jsonc` and the `npm run deploy` script.

See the [software documentation](documentation/software/) for configuration, authentication, and deployment details. The `scripts/deploy.ps1` shortcut expects a server-side `deploy/deploy.sh` script that is not included in this repository.

## Documentation

- [Software guides](documentation/software/) — web application usage, architecture, APIs, development, and deployment.
- [Hardware guide](documentation/hardware/) — station prototype setup and configuration.
- [Simulation guides](documentation/simulation/) — simulator usage, architecture, and experiments.

For simulator commands and experiment details, see [`simulation/README.md`](simulation/README.md).
