package com.dtback.dt_back.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Getter @Setter
public class Warehouse {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer warehouseId;

    private String warehouseName;
    private String warehouseCode;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "company_id")
    private Company company;

    @OneToMany(mappedBy = "warehouse")
    private List<AGV> agvs = new ArrayList<>();
}
