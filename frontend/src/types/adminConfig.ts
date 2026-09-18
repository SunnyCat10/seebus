export interface StationConfig {
    id: string;
    name: string;
}

export interface BusConfig {
    id: string;
    name: string;
    capacity: number;
}

export interface ScheduleEntryConfig {
    busId: string;
    stationId: string;
    time: string;
}

export interface AdminConfig {
    stations: StationConfig[];
    buses: BusConfig[];
    defaultSchedule: ScheduleEntryConfig[];
}