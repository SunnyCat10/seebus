import type { CurrentSchedule } from "../types/schedule";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ??
    "https://seebus.bolognese.dev";

export async function getCurrentSchedule(): Promise<CurrentSchedule> {
    const response = await fetch(
        `${API_BASE_URL}/api/schedule/current`,
    );

    if (!response.ok) {
        throw new Error("Failed to load current schedule");
    }

    return response.json();
}