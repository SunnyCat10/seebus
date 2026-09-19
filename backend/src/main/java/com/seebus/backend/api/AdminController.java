package com.seebus.backend.api;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @GetMapping("/verify")
    public ResponseEntity<Void> verifyAdmin() {
        return ResponseEntity.noContent().build();
    }
}
