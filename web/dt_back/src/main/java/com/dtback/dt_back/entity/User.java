package com.dtback.dt_back.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Getter
@Setter
@Table(name = "user")
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer userId;

    private String email;
    private String password;
    private String userName;
    private String phoneNumber;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "warehouse_id")
    private Warehouse warehouse;
}
