import { useState } from "react";

import { updateAdminConfig } from "../api/seebusApi";

import type {
    AdminConfig,
    BusConfig,
    ScheduleEntryConfig,
    StationConfig,
} from "../types/adminConfig";

export function AdminPage() {
    const [adminToken, setAdminToken] = useState("");

    const [stations, setStations] = useState<StationConfig[]>([]);
    const [buses, setBuses] = useState<BusConfig[]>([]);
    const [schedule, setSchedule] =
        useState<ScheduleEntryConfig[]>([]);

    const [status, setStatus] = useState<string | null>(null);

    function addStation() {
        setStations([
            ...stations,
            {
                id: "",
                name: "",
            },
        ]);
    }

    function addBus() {
        setBuses([
            ...buses,
            {
                id: "",
                name: "",
                capacity: 50,
            },
        ]);
    }

    function addScheduleEntry() {
        setSchedule([
            ...schedule,
            {
                busId: buses[0]?.id ?? "",
                stationId: stations[0]?.id ?? "",
                time: "12:00",
            },
        ]);
    }

    async function saveConfiguration() {
        const config: AdminConfig = {
            stations,
            buses,
            defaultSchedule: schedule,
        };

        try {
            setStatus("Saving...");

            await updateAdminConfig(
                config,
                adminToken,
            );

            setStatus("Configuration saved.");
        } catch (error) {
            if (error instanceof Error) {
                setStatus(`Failed: ${error.message}`);
            } else {
                setStatus("Failed to save configuration.");
            }
        }
    }

    return (
        <main>
            <h1>Seebus Admin</h1>

            <section>
                <h2>Authentication</h2>

                <input
                    type="password"
                    placeholder="Admin token"
                    value={adminToken}
                    onChange={(event) =>
                        setAdminToken(event.target.value)
                    }
                />
            </section>

            <section>
                <h2>Stations</h2>

                {stations.map((station, index) => (
                    <div key={index}>
                        <input
                            placeholder="Station ID"
                            value={station.id}
                            onChange={(event) => {
                                const updated = [...stations];

                                updated[index] = {
                                    ...station,
                                    id: event.target.value,
                                };

                                setStations(updated);
                            }}
                        />

                        <input
                            placeholder="Station name"
                            value={station.name}
                            onChange={(event) => {
                                const updated = [...stations];

                                updated[index] = {
                                    ...station,
                                    name: event.target.value,
                                };

                                setStations(updated);
                            }}
                        />

                        <button
                            type="button"
                            onClick={() =>
                                setStations(
                                    stations.filter((_, i) => i !== index),
                                )
                            }
                        >
                            Remove
                        </button>
                    </div>
                ))}

                <button type="button" onClick={addStation}>
                    Add station
                </button>
            </section>

            <section>
                <h2>Buses</h2>

                {buses.map((bus, index) => (
                    <div key={index}>
                        <input
                            placeholder="Bus ID"
                            value={bus.id}
                            onChange={(event) => {
                                const updated = [...buses];

                                updated[index] = {
                                    ...bus,
                                    id: event.target.value,
                                };

                                setBuses(updated);
                            }}
                        />

                        <input
                            placeholder="Bus name"
                            value={bus.name}
                            onChange={(event) => {
                                const updated = [...buses];

                                updated[index] = {
                                    ...bus,
                                    name: event.target.value,
                                };

                                setBuses(updated);
                            }}
                        />

                        <input
                            type="number"
                            min="1"
                            value={bus.capacity}
                            onChange={(event) => {
                                const updated = [...buses];

                                updated[index] = {
                                    ...bus,
                                    capacity: Number(event.target.value),
                                };

                                setBuses(updated);
                            }}
                        />

                        <button
                            type="button"
                            onClick={() =>
                                setBuses(
                                    buses.filter((_, i) => i !== index),
                                )
                            }
                        >
                            Remove
                        </button>
                    </div>
                ))}

                <button type="button" onClick={addBus}>
                    Add bus
                </button>
            </section>

            <section>
                <h2>Default schedule</h2>

                {schedule.map((entry, index) => (
                    <div key={index}>
                        <select
                            value={entry.busId}
                            onChange={(event) => {
                                const updated = [...schedule];

                                updated[index] = {
                                    ...entry,
                                    busId: event.target.value,
                                };

                                setSchedule(updated);
                            }}
                        >
                            <option value="">
                                Select bus
                            </option>

                            {buses.map((bus) => (
                                <option key={bus.id} value={bus.id}>
                                    {bus.name || bus.id}
                                </option>
                            ))}
                        </select>

                        <select
                            value={entry.stationId}
                            onChange={(event) => {
                                const updated = [...schedule];

                                updated[index] = {
                                    ...entry,
                                    stationId: event.target.value,
                                };

                                setSchedule(updated);
                            }}
                        >
                            <option value="">
                                Select station
                            </option>

                            {stations.map((station) => (
                                <option
                                    key={station.id}
                                    value={station.id}
                                >
                                    {station.name || station.id}
                                </option>
                            ))}
                        </select>

                        <input
                            type="time"
                            value={entry.time}
                            onChange={(event) => {
                                const updated = [...schedule];

                                updated[index] = {
                                    ...entry,
                                    time: event.target.value,
                                };

                                setSchedule(updated);
                            }}
                        />

                        <button
                            type="button"
                            onClick={() =>
                                setSchedule(
                                    schedule.filter((_, i) => i !== index),
                                )
                            }
                        >
                            Remove
                        </button>
                    </div>
                ))}

                <button
                    type="button"
                    onClick={addScheduleEntry}
                    disabled={stations.length === 0 || buses.length === 0}
                >
                    Add schedule entry
                </button>
            </section>

            <hr />

            <button
                type="button"
                onClick={saveConfiguration}
                disabled={!adminToken}
            >
                Save configuration
            </button>

            {status && <p>{status}</p>}
        </main>
    );
}