package com.seebus.backend.schedule;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.station.Station;

import java.time.ZonedDateTime;

public record ScheduledStopResponse(
        Bus bus,
        Station station,
        ZonedDateTime arrivalTime
) {
}
