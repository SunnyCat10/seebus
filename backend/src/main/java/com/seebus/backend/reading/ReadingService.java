package com.seebus.backend.reading;

import com.seebus.backend.station.StationService;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;

@Service
public class ReadingService {
    private final ConcurrentLinkedQueue<StationReading> readings = new ConcurrentLinkedQueue<>();

    private final StationService stationService;

    public ReadingService(StationService stationService) {
        this.stationService = stationService;
    }

    public StationReading addReading(StationReadingRequest request) {

        if (!stationService.exists(request.stationId())) {
            throw new IllegalArgumentException(
                    "Unknown station: " + request.stationId()
            );
        }
        
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
