package ru.climacore.alice.services;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class ScBridgeService {

    private final RestTemplate rest = new RestTemplate();
    private final String bridgeUrl = "http://localhost:3000/sc/query";

    public Map<String, Object> send(Map<String, Object> body) {
        return rest.postForObject(bridgeUrl, body, Map.class);
    }
}
