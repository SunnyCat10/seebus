package com.seebus.backend.bus;

import org.springframework.stereotype.Service;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class BusService {
    private final Map<String, Bus> buses = new ConcurrentHashMap<>();

    public Collection<Bus> getBuses() {
        return List.copyOf(buses.values());
    }

    public Bus getBus(String id) {
        return buses.get(id);
    }

    public boolean exists(String id) {
        return buses.containsKey(id);
    }

    public void replaceAll(Collection<Bus> newBuses) {
        buses.clear();

        for (Bus bus : newBuses) {
            buses.put(bus.id(), bus);
        }
    }
}
