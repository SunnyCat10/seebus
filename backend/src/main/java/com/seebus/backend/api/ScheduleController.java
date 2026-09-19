package com.seebus.backend.api;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.bus.BusService;
import com.seebus.backend.schedule.*;
import com.seebus.backend.station.Station;
import com.seebus.backend.station.StationService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/schedule")
public class ScheduleController {

    private final ScheduleService scheduleService;
    private final SchedulingService schedulingService;
    private final BusService busService;
    private final StationService stationService;

    public ScheduleController(ScheduleService scheduleService, SchedulingService schedulingService,
                              BusService busService, StationService stationService) {
        this.scheduleService = scheduleService;
        this.schedulingService = schedulingService;
        this.busService = busService;
        this.stationService = stationService;
    }

    @GetMapping("/default")
    public List<ScheduleEntry> getDefaultSchedule() {
        return scheduleService.getDefaultSchedule();
    }

    @GetMapping("/current")
    public CurrentScheduleResponse getCurrentSchedule() {
        CurrentSchedule current =
                schedulingService.getCurrentSchedule();

        List<ScheduledStopResponse> entries =
                current.entries()
                        .stream()
                        .map(this::toResponse)
                        .toList();

        return new CurrentScheduleResponse(
                current.generatedAt(),
                current.policy(),
                entries
        );
    }

    private ScheduledStopResponse toResponse(
            ScheduledStop entry
    ) {
        Bus bus =
                busService.getBus(entry.busId());

        Station station =
                stationService.getStation(entry.stationId());

        return new ScheduledStopResponse(
                bus,
                station,
                entry.arrivalTime()
        );
    }
}