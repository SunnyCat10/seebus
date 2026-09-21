package com.seebus.backend.schedule;

import com.seebus.backend.bus.BusService;
import com.seebus.backend.reading.ReadingService;
import com.seebus.backend.station.StationService;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

@Service
public class SchedulingService {

    private final StationService stationService;
    private final BusService busService;
    private final ScheduleService scheduleService;
    private final ReadingService readingService;
    private final SchedulingPolicyService policyService;

    private final AtomicReference<CurrentSchedule> currentSchedule =  new AtomicReference<>(
            new CurrentSchedule(
                    Instant.now(),
                    "none",
                    List.of()
            )
    );

    public SchedulingService(
            StationService stationService,
            BusService busService,
            ScheduleService scheduleService,
            ReadingService readingService,
            SchedulingPolicyService policyService
    ) {
        this.stationService = stationService;
        this.busService = busService;
        this.scheduleService = scheduleService;
        this.readingService = readingService;
        this.policyService = policyService;
    }

    public void recalculate() {
        ZonedDateTime now = ZonedDateTime.now();

        SchedulingInput input = new SchedulingInput(
                now,
                List.copyOf(stationService.getStations()),
                List.copyOf(busService.getBuses()),
                scheduleService.getDefaultSchedule(),
                readingService.getLastestReadingsSnapshot()
        );

        SchedulingPolicy currentPolicy = policyService.getActivePolicy();
        CurrentSchedule result = currentPolicy.calculateSchedule(input);

        currentSchedule.set(result);
    }

    public CurrentSchedule getCurrentSchedule() {
        return currentSchedule.get();
    }
}
