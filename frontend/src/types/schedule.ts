export interface ScheduledStop {
    busId: string;
    stationId: string;
    arrivalTime: string;
}

export interface CurrentSchedule {
    generatedAt: string;
    policy: string;
    entries: ScheduledStop[];
}