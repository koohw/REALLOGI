package com.dtback.dt_back.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Getter @Setter
public class AGV {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer agvId;
    private String agvName;

    private String agvCode;
    private String agvModel;

    private Integer warehouseId;

    private String agvFootnote;

}
