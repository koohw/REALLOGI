package com.dtback.dt_back;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@SpringBootApplication
//@EnableJpaRepositories(basePackages = "com.dtback.dt_back.repository")
public class DtBackApplication {

    public static void main(String[] args) {
        SpringApplication.run(DtBackApplication.class, args);
    }

}
