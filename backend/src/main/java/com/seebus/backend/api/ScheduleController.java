package com.seebus.backend.api;

import com.seebus.backend.schedule.CurrentSchedule;
import com.seebus.backend.schedule.ScheduleEntry;
import com.seebus.backend.schedule.ScheduleService;
import com.seebus.backend.schedule.SchedulingService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/schedule")
public class ScheduleController {

    private final ScheduleService scheduleService;
    private final SchedulingService schedulingService;

    public ScheduleController(ScheduleService scheduleService, SchedulingService schedulingService) {
        this.scheduleService = scheduleService;
        this.schedulingService = schedulingService;
    }

    @GetMapping("/default")
    public List<ScheduleEntry> getDefaultSchedule() {
        return scheduleService.getDefaultSchedule();
    }

    @GetMapping("/current")
    public CurrentSchedule getCurrentSchedule() {
        return schedulingService.getCurrentSchedule();
    }
}