package com.seebus.backend.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

@Component
public class ApiTokenAuthenticationFilter extends OncePerRequestFilter {

    private final String sensorToken;
    private final String adminToken;

    public ApiTokenAuthenticationFilter(
            @Value("${seebus.security.sensor-token}") String sensorToken,
            @Value("${seebus.security.admin-token}") String adminToken) {
        this.sensorToken = sensorToken;
        this.adminToken = adminToken;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);

        if (header != null && header.startsWith("Bearer ")) {

            String token = header.substring(7);

            if (matches(token, adminToken)) {
                authenticate(
                        "admin",
                        "ROLE_ADMIN"
                );
            } else if  (matches(token, sensorToken)) {
                authenticate(
                        "sensor",
                        "ROLE_SENSOR"
                );
            }
        }

        filterChain.doFilter(request, response);
    }

    private void authenticate(String principal, String role) {
        var authentication = new UsernamePasswordAuthenticationToken(
                principal, null, List.of(new SimpleGrantedAuthority(role)));

        SecurityContextHolder.getContext().setAuthentication(authentication);
    }

    private boolean matches(
            String supplied,
            String expected
    ) {
        return MessageDigest.isEqual(
                supplied.getBytes(StandardCharsets.UTF_8),
                expected.getBytes(StandardCharsets.UTF_8)
        );
    }
}
