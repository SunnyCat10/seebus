package com.seebus.backend.api;

import com.seebus.backend.config.AdminConfigRequest;
import com.seebus.backend.config.AdminConfigResponse;
import com.seebus.backend.config.ConfigService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/config")
public class AdminConfigController {

    private final ConfigService configService;

    public AdminConfigController(ConfigService configService) {
        this.configService = configService;
    }

    @PutMapping
    public ResponseEntity<Void> updateConfiguration(@Valid @RequestBody AdminConfigRequest request) {
        configService.updateConfiguration(request);

        return ResponseEntity.noContent().build();
    }

    @GetMapping
    public AdminConfigResponse getConfiguration() {
        return configService.getConfiguration();
    }
}
