import type {Bus} from "./bus.ts";
import type {Station} from "./station.ts";

export interface ScheduledStop {
    bus: Bus;
    station: Station;
    arrivalTime: string;
}

export interface CurrentSchedule {
    generatedAt: string;
    policy: string;
    entries: ScheduledStop[];
}