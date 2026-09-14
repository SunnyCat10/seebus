package com.seebus.backend.reading;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

public record StationReadingRequest (
    @NotBlank
    String stationId,
    @NotNull
    @DecimalMin("0.0")
    @DecimalMax("1.0")
    Double occupancy,

    @NotNull
    Instant measuredAt
    ) {
}
