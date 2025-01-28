package com.dtback.dt_back.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new LoginCheckInterceptor())
                .addPathPatterns("/api/**")  // 모든 API 경로에 인터셉터 적용
                .excludePathPatterns(
                        "/api/users/login",      // 로그인 경로 제외
                        "/api/users/signup" ,
                        "/api/users/warehouses/*",// 회원가입 경로 제외
                        "/api/companies"
                );
    }
}