package com.dtback.dt_back.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
@Table(name = "agv_log")
public class AGVLog {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer logId;

    private Integer logCode;
    private Float locationX;
    private Float locationY;
    private Float efficiency;
    private String state;
    private String significant;

    @Column(name = "log_time")
    private LocalDateTime logTime;


    private Integer agv_id;
}