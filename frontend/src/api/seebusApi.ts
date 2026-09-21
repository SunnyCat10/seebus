import type { CurrentSchedule } from "../types/schedule";
import type { AdminConfig } from "../types/adminConfig";
import type {PolicyInfo} from "../types/policy.ts";
import type {StationReading} from "../types/reading.ts";

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

export async function updateAdminConfig(config: AdminConfig, adminToken: string): Promise<void> {
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

export const getAdminConfig = async (adminToken: string): Promise<AdminConfig> => {
    const response = await fetch(
        `${API_BASE_URL}/api/admin/config`,
        {
            headers: {
                Authorization: `Bearer ${adminToken}`,
            },
        },
    );

    if (!response.ok) {
        throw new Error(
            "Could not load configuration",
        );
    }

    const config =
        await response.json() as AdminConfig;

    return {
        ...config,

        defaultSchedule:
            config.defaultSchedule.map(
                (entry) => ({
                    ...entry,
                    time: normalizeScheduleTime(
                        entry.time,
                    ),
                }),
            ),
    };
};

export async function verifyAdminToken(token: string): Promise<boolean> {
    const response = await fetch(
        `${API_BASE_URL}/api/admin/verify`,
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        },
    );

    return response.ok;
}

export async function getPolicy(adminToken: string): Promise<PolicyInfo> {
    const response = await fetch(
        `${API_BASE_URL}/api/admin/policy`,
        {
            headers: {
                Authorization: `Bearer ${adminToken}`,
            },
        },
    );

    if (!response.ok) {
        throw new Error("Failed to load scheduling policy");
    }

    return response.json();
}

export async function updatePolicy(policy: string, adminToken: string): Promise<PolicyInfo> {
    const response = await fetch(
        `${API_BASE_URL}/api/admin/policy`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${adminToken}`,
            },
            body: JSON.stringify({
                policy,
            }),
        },
    );

    if (!response.ok) {
        const text = await response.text();

        throw new Error(
            text || `Request failed with status ${response.status}`,
        );
    }

    return response.json();
}

export async function getReadings(adminToken: string): Promise<StationReading[]> {
    const response = await fetch(
        `${API_BASE_URL}/api/readings`,
        {
            headers: {
                Authorization: `Bearer ${adminToken}`,
            },
        },
    );

    if (!response.ok) {
        throw new Error("Could not load readings");
    }

    return response.json();
}

export async function getLatestReadings(adminToken: string): Promise<Record<string, StationReading>> {
    const response = await fetch(
        `${API_BASE_URL}/api/readings/latest`,
        {
            headers: {
                Authorization: `Bearer ${adminToken}`,
            },
        },
    );

    if (!response.ok) {
        throw new Error(
            "Could not load latest readings",
        );
    }

    return response.json();
}

const normalizeScheduleTime = (value: string): string => {
    const [hour, minute] = value.split(":");

    if (!hour || !minute) {
        return value;
    }

    return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
};