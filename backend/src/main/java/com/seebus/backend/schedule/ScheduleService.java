package com.seebus.backend.schedule;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

@Service
public class ScheduleService {

    private final List<ScheduleEntry> defaultSchedule =
            new ArrayList<>();

    public List<ScheduleEntry> getDefaultSchedule() {
        return List.copyOf(defaultSchedule);
    }

    public void replaceAll(Collection<ScheduleEntry> entries) {
        defaultSchedule.clear();
        defaultSchedule.addAll(entries);
    }
}
