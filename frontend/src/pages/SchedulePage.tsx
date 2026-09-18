import { useEffect, useState } from "react";

import { getCurrentSchedule } from "../api/seebusApi";
import type { CurrentSchedule } from "../types/schedule";

export function SchedulePage() {
    const [schedule, setSchedule] =
        useState<CurrentSchedule | null>(null);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadSchedule() {
            try {
                const result = await getCurrentSchedule();

                setSchedule(result);
                setError(null);
            } catch {
                setError("Could not load the current schedule.");
            }
        }

        loadSchedule();

        const interval = setInterval(loadSchedule, 60000);

        return () => clearInterval(interval);
    }, []);

    return (
        <main>
            <h1>Seebus</h1>
            <h2>Upcoming schedule</h2>

            {error && <p>{error}</p>}

            {!schedule && !error && (
                <p>Loading...</p>
            )}

            {schedule?.entries.map((entry) => (
                <div
                    key={`${entry.busId}-${entry.stationId}-${entry.arrivalTime}`}
                >
                    <strong>
                        {new Date(entry.arrivalTime)
                            .toLocaleTimeString()}
                    </strong>

                    {" — "}
                    {entry.stationId}
                    {" — "}
                    {entry.busId}
                </div>
            ))}
        </main>
    );
}