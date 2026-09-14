package com.seebus.backend.reading;

import java.time.Instant;
import java.util.UUID;

public record StationReading(
        UUID id,
        String stationId,
        double occupancy,
        Instant measuredAt,
        Instant receivedAt
) {
}