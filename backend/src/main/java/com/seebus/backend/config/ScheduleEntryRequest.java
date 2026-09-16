package com.seebus.backend.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.LocalTime;

public record ScheduleEntryRequest(
        @NotBlank
        String busId,

        @NotBlank
        String stationId,

        @NotNull
        LocalTime time
) {
}
