package com.seebus.backend.schedule;

import java.time.Instant;
import java.util.List;

public record CurrentScheduleResponse(
        Instant generatedAt,
        String policy,
        List<ScheduledStopResponse> entries
) {
}
