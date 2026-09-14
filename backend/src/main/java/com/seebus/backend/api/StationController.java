package com.seebus.backend.api;

import com.seebus.backend.station.CreateStationRequest;
import com.seebus.backend.station.Station;
import com.seebus.backend.station.StationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Collection;

@RestController
@RequestMapping("/api/stations")
public class StationController {

    private final StationService stationService;

    public StationController(StationService stationService) {
        this.stationService = stationService;
    }

    @GetMapping
    public Collection<Station> getStations() {
        return stationService.getStations();
    }

    @PostMapping
    public ResponseEntity<Station> addStation(@Valid @RequestBody CreateStationRequest request) {
        Station station = new Station(request.id(), request.name());
        boolean stationAdded = stationService.addStation(station);

        if (!stationAdded) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }

        return ResponseEntity.ok(station);
    }
}
