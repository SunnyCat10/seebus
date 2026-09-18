package com.seebus.backend.schedule;

import java.time.Instant;
import java.util.List;

public record CurrentSchedule(
        Instant generatedAt,
        String policy,
        List<ScheduledStop> entries
) {
}
