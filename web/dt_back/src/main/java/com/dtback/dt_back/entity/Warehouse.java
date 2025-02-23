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

    private Integer companyId;
}
