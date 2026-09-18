import type { CurrentSchedule } from "../types/schedule";
import type { AdminConfig } from "../types/adminConfig";

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

export async function updateAdminConfig(
    config: AdminConfig,
    adminToken: string,
): Promise<void> {
    const response = await fetch(
        `${API_BASE_URL}/api/admin/config`,
        {
            method: "PUT",

            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${adminToken}`,
            },

            body: JSON.stringify(config),
        },
    );

    if (!response.ok) {
        const text = await response.text();

        throw new Error(
            text || `Request failed with status ${response.status}`,
        );
    }
}