package com.seebus.backend.config;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.schedule.ScheduleEntry;
import com.seebus.backend.station.Station;

import java.util.Collection;
import java.util.List;

public record AdminConfigResponse(
        Collection<Station> stations,
        Collection<Bus> buses,
        List<ScheduleEntry> defaultSchedule
) {
}
