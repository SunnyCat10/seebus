package com.seebus.backend.api;

import com.seebus.backend.reading.ReadingService;
import com.seebus.backend.reading.StationReading;
import com.seebus.backend.reading.StationReadingRequest;
import jakarta.validation.Valid;
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
    public ResponseEntity<StationReading> addReading(@Valid @RequestBody StationReadingRequest request) {
        StationReading reading = readingService.addReading(request);

        return ResponseEntity.created(URI.create("/api/readings" + reading.id())).body(reading);
    }

    @GetMapping
    public List<StationReading> getReadings() {
        return readingService.getReadings();
    }

}
