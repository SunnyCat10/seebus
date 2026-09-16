package com.seebus.backend.config;

import com.seebus.backend.bus.Bus;
import com.seebus.backend.bus.BusService;
import com.seebus.backend.schedule.ScheduleEntry;
import com.seebus.backend.schedule.ScheduleService;
import com.seebus.backend.station.CreateStationRequest;
import com.seebus.backend.station.Station;
import com.seebus.backend.station.StationService;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class ConfigService {

    private final StationService stationService;
    private final BusService busService;
    private final ScheduleService scheduleService;

    public ConfigService(StationService stationService, BusService busService, ScheduleService scheduleService) {
        this.stationService = stationService;
        this.busService = busService;
        this.scheduleService = scheduleService;
    }

    public void updateConfiguration(AdminConfigRequest request) {

        validateConfiguration(request);

        List<Station> stations = request.stations().stream().map(
           s -> new Station(s.id(), s.name())
        ).toList();

        List<Bus> buses = request.buses().stream().map(
                b -> new Bus(b.id(), b.name(), b.capacity())
        ).toList();

        List<ScheduleEntry> schedule = request.defaultSchedule().stream().map(
                s -> new ScheduleEntry(s.busId(), s.stationId(), s.time())
        ).toList();

        stationService.replaceAll(stations);
        busService.replaceAll(buses);
        scheduleService.replaceAll(schedule);
    }

    private void validateConfiguration(AdminConfigRequest request) {
        Set<String> stationIds = new HashSet<String>();

        for (CreateStationRequest station : request.stations()) {
            if (!stationIds.add(station.id())) {
                throw new IllegalArgumentException(
                        "Duplicate station id: " + station.id()
                );
            }
        }

        Set<String> busIds = new HashSet<String>();

        for (BusConfigRequest bus: request.buses()) {
            if (!busIds.add(bus.id())) {
                throw new IllegalArgumentException(
                        "Duplicate bus id: " + bus.id()
                );
            }
        }

        for (ScheduleEntryRequest entry : request.defaultSchedule()) {

            if (!stationIds.contains(entry.stationId())) {
                throw new IllegalArgumentException(
                        "Unknown station in schedule: "
                                + entry.stationId()
                );
            }

            if (!busIds.contains(entry.busId())) {
                throw new IllegalArgumentException(
                        "Unknown bus in schedule: "
                                + entry.busId()
                );
            }
        }
    }
}
