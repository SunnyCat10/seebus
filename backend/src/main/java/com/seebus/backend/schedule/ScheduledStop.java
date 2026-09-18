package com.seebus.backend.schedule;

import java.time.ZonedDateTime;

public record ScheduledStop(
        String busId,
        String stationId,
        ZonedDateTime arrivalTime
) {
}
