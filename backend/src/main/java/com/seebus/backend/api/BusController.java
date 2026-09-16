package com.seebus.backend.api;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.bus.BusService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Collection;

@RestController
@RequestMapping("/api/buses")
public class BusController {

    private final BusService busService;

    public BusController(BusService busService) {
        this.busService = busService;
    }

    @GetMapping
    public Collection<Bus> getBuses() {
        return busService.getBuses();
    }
}