package com.dtback.dt_back.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Slf4j
@Component
public class LoginCheckInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String requestURI = request.getRequestURI();
        log.info("인터셉터 실행 - 요청 URI: {}", requestURI);

        if(request.getMethod().equals("OPTIONS")){
            return true;
        }

        // 로그인 관련 URI는 체크하지 않음
        if (requestURI.contains("/login") || requestURI.contains("/signup")) {
            log.info("로그인/회원가입 요청으로 인터셉터 통과");
            return true;
        }

        HttpSession session = request.getSession(false);
        if (session == null || session.getAttribute("USER") == null) {
            log.info("미인증 사용자 요청");
            if (session == null){
                log.info("session is null");
            }else if (session.getAttribute("USER") == null){
                log.info("user is null");
            }

            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "로그인이 필요합니다");
            return false;
        }

        return true;
    }
}
