package com.seebus.backend.api;

import com.seebus.backend.schedule.ScheduleEntry;
import com.seebus.backend.schedule.ScheduleService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/schedule")
public class ScheduleController {

    private final ScheduleService scheduleService;

    public ScheduleController(ScheduleService scheduleService) {
        this.scheduleService = scheduleService;
    }

    @GetMapping("/default")
    public List<ScheduleEntry> getDefaultSchedule() {
        return scheduleService.getDefaultSchedule();
    }
}