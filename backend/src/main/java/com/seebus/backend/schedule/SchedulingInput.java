package com.seebus.backend.schedule;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.reading.StationReading;
import com.seebus.backend.station.Station;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;

public record SchedulingInput(
        ZonedDateTime now,
        List<Station> stations,
        List<Bus> buses,
        List<ScheduleEntry> defaultSchedule,
        Map<String, StationReading> latestReadings
) {
}
