package com.seebus.backend.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record BusConfigRequest (
    @NotBlank
    String id,

    @NotBlank
    String name,

    @NotNull
    @Positive
    Integer capacity
) {
}