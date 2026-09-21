package com.seebus.backend.reading;

import com.seebus.backend.station.Station;
import com.seebus.backend.station.StationService;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;

@Service
public class ReadingService {
    private static final int MAX_READINGS = 100;

    private final ArrayDeque<StationReading> readings = new ArrayDeque<>(MAX_READINGS);
    private final Object readingLock = new Object();

    private final ConcurrentHashMap<String, StationReading> lastestReading = new ConcurrentHashMap<>();
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

        addToHistory(reading);

        lastestReading.compute(
                reading.stationId(),
                (stationId, current) -> {
                    if (current == null) {
                        return reading;
                    }

                    if (reading.measuredAt().isAfter(current.measuredAt())) {
                        return reading;
                    }

                    return current;
                });

        return reading;
    }

    public void addToHistory(StationReading reading) {
        synchronized (readingLock) {
            if (readings.size() >= MAX_READINGS) {
                readings.removeFirst();
            }

            readings.addLast(reading);
        }
    }

    public List<StationReading> getReadings() {
        synchronized (readingLock) {
            return List.copyOf(this.readings);
        }
    }

    public Map<String, StationReading> getLastestReadingsSnapshot() {
        return Map.copyOf(lastestReading);
    }
}
