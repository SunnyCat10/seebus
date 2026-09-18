package com.seebus.backend.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

@Configuration
public class SecurityConfig {

    @Bean
    public UrlBasedCorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();

        configuration.setAllowedOrigins(List.of(
                "https://seebus.bolognese.dev",
                "http://localhost:5173"
        ));

        configuration.setAllowedMethods(List.of(
                "GET", "POST", "PUT", "DELETE", "OPTIONS"
        ));

        configuration.setAllowedHeaders(List.of(
                "Authorization",
                "Content-Type"
        ));

        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source =
                new UrlBasedCorsConfigurationSource();

        source.registerCorsConfiguration(
                "/api/**",
                configuration
        );

        return source;
    }

    @Bean
    SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            ApiTokenAuthenticationFilter tokenFilter
    ) throws Exception {
        http.cors(
                Customizer.withDefaults()).csrf(AbstractHttpConfigurer::disable).sessionManagement(
                session -> session.sessionCreationPolicy(
                        SessionCreationPolicy.STATELESS).disable().authorizeHttpRequests(
                                auth -> auth

                                    // Public:
                                        .requestMatchers(
                                                HttpMethod.GET,
                                                "/api/health",
                                                "/api/schedule/current")
                                        .permitAll()

                                    // ESP32 device:
                                        .requestMatchers(
                                                HttpMethod.POST,
                                                "/api/readings"
                                        ).hasRole("SENSOR")

                                    // Admin general endpoints:
                                        .requestMatchers(
                                                "/api/admin/**"
                                        ).hasRole("ADMIN")

                                    // Admin management/read endpoints:
                                        .requestMatchers(
                                                "/api/stations/**",
                                                "/api/buses/**",
                                                "/api/readings/**",
                                                "/api/schedule/default"
                                        ).hasRole("ADMIN")

                                    // Default deny all to not expose something new:
                                        .anyRequest().denyAll()
                ).exceptionHandling(ex -> ex.authenticationEntryPoint(
                        (request, response, exception) ->
                            response.sendError(HttpServletResponse.SC_UNAUTHORIZED)).accessDeniedHandler(
                        (request, response, exception) ->
                                response.sendError(HttpServletResponse.SC_FORBIDDEN)
                ))
                        .httpBasic(AbstractHttpConfigurer::disable)
                        .formLogin(AbstractHttpConfigurer::disable)
                        .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class)
        );

        return http.build();
    }
}
