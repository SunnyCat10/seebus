package com.seebus.backend.reading;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;

@Service
public class ReadingService {
    private final ConcurrentLinkedQueue<StationReading> readings = new ConcurrentLinkedQueue<>();

    public StationReading addReading(StationReadingRequest request) {
        StationReading reading = new StationReading(
                UUID.randomUUID(),
                request.stationId(),
                request.occupancy(),
                request.measuredAt(),
                Instant.now()
        );

        readings.add(reading);

        return reading;
    }

    public List<StationReading> getReadings() {
        return List.copyOf(this.readings);
    }
}
