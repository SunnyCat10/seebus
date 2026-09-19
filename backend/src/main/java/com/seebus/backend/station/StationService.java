package com.seebus.backend.station;

import org.springframework.stereotype.Service;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class StationService {

    private final Map<String, Station> stations = new ConcurrentHashMap<>();

    public boolean addStation(Station station) {
        Station previous = stations.putIfAbsent(station.id(), station);
        return previous == null;
    }

    public Collection<Station> getStations() {
        return List.copyOf(stations.values());
    }

    public Station getStation(String id) {
        return stations.get(id);
    }

    public boolean exists(String id) {
        return stations.containsKey(id);
    }

    public void replaceAll(Collection<Station> newStations) {
        stations.clear();

        for (Station station : newStations) {
            stations.put(station.id(), station);
        }
    }

}
