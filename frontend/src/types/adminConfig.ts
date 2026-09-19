import type {Bus} from "./bus.ts";
import type {Station} from "./station.ts";

export interface ScheduleEntryConfig {
    busId: string;
    stationId: string;
    time: string;
}

export interface AdminConfig {
    stations: Station[];
    buses: Bus[];
    defaultSchedule: ScheduleEntryConfig[];
}