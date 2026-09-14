package com.seebus.backend.reading;

import java.time.Instant;

public record StationReadingRequest (
    String stationId,
    Double occupancy,
    Instant measuredAt
    ) {
}
