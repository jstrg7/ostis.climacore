package ru.climacore.alice.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.climacore.alice.services.ScBridgeService;
import ru.climacore.alice.services.YandexNotifyService;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/alice")
public class AliceController {

    private final ScBridgeService scBridge;
    private final YandexNotifyService yandexNotify;

    public AliceController(ScBridgeService scBridge, YandexNotifyService yandexNotify) {
        this.scBridge = scBridge;
        this.yandexNotify = yandexNotify;
    }

    @PostMapping
    public ResponseEntity<Map<String,Object>> handle(@RequestBody Map<String,Object> body) {
        Map<String,Object> request = (Map<String,Object>) body.get("request");
        Map<String,Object> session = (Map<String,Object>) body.get("session");
        String command = (String) request.get("command"); // пользовательская фраза

        // Простейшее распарсивание — можно заменить NLU / intent mapping
        if (command == null) command = "";

        // Общий запрос к OSTIS (например — запрос информации)
        Map<String, Object> payload = new HashMap<>();
        payload.put("action", "ask");
        payload.put("text", command);

        Map<String, Object> scResp = scBridge.send(payload);

        String answer = buildTextFromScResponse(scResp);
        return ResponseEntity.ok(makeAliceResponse(answer, session, false));
    }

    private Map<String,Object> makeAliceResponse(String text, Map<String,Object> session, boolean endSession) {
        Map<String,Object> response = new HashMap<>();
        Map<String,Object> r = new HashMap<>();
        r.put("text", text);
        r.put("end_session", endSession);
        response.put("response", r);
        response.put("session", Map.of(
                "session_id", session.get("session_id"),
                "message_id", session.get("message_id"),
                "user_id", session.get("user_id")
        ));
        response.put("version", "1.0");
        return response;
    }

    private String buildTextFromScResponse(Map<String,Object> scResp) {
        // примитив: извлечь поле "text" из ответа bridge
        return scResp.getOrDefault("text", "Не могу ответить").toString();
    }
}
