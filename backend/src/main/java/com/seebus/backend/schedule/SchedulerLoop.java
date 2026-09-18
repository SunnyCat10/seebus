package com.seebus.backend.schedule;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class SchedulerLoop {

    private final SchedulingService schedulingService;

    public SchedulerLoop(SchedulingService schedulingService) {
        this.schedulingService = schedulingService;
    }

    @Scheduled(fixedDelayString = "${seebus.scheduler.interval-ms:5000}")
    public void tick() {
        schedulingService.recalculate();
    }
}
