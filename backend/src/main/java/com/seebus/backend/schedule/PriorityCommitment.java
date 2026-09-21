package com.seebus.backend.schedule;

import java.time.ZonedDateTime;

public record PriorityCommitment(
        ScheduledStop originalStop,
        ZonedDateTime arrivalTime
) {
}
