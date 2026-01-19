package services;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

@Service
public class YandexNotifyService {
    private final RestTemplate rest = new RestTemplate();
    private final String token = "BEARER_OR_OAUTH_TOKEN"; // смотрите доку авторизации
    private final String base = "https://dialogs.yandex.net/api/v1/skills"; // проверьте актуальную URL в доке

    public void notifyStateChange(String skillId, String deviceId, Map<String,Object> state) {
        String url = base + "/" + skillId + "/callback/state";
        Map<String,Object> body = Map.of(
                "devices", List.of(Map.of(
                        "id", deviceId,
                        "state", state,
                        "reach_state", true
                ))
        );
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(token);
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String,Object>> e = new HttpEntity<>(body, headers);
        rest.postForEntity(url, e, String.class);
    }
}
