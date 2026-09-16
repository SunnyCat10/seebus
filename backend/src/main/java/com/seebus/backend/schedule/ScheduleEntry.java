package com.seebus.backend.schedule;

import java.time.LocalTime;

public record ScheduleEntry(
        String busId,
        String stationId,
        LocalTime time
) {
}
