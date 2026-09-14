package com.seebus.backend.api;

import com.seebus.backend.reading.ReadingService;
import com.seebus.backend.reading.StationReading;
import com.seebus.backend.reading.StationReadingRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/readings")
public class ReadingController {

    private final ReadingService readingService;

    public ReadingController(ReadingService readingService) {
        this.readingService = readingService;
    }

    @PostMapping
    public ResponseEntity<StationReading> addReading(@RequestBody StationReadingRequest request) {

        if (request.stationId() == null || request.stationId().isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        if (request.occupancy() == null || request.occupancy() < 0 || request.occupancy() > 1) {
            return ResponseEntity.badRequest().build();
        }
        
        if (request.measuredAt() == null) {
            return ResponseEntity.badRequest().build();
        }

        StationReading reading = readingService.addReading(request);

        return ResponseEntity.created(URI.create("/api/readings" + reading.id())).body(reading);
    }

    @GetMapping
    public List<StationReading> getReadings() {
        return readingService.getReadings();
    }

}
