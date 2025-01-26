package com.dtback.dt_back.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Getter @Setter
public class AGV {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer agvId;

    private String agvCode;
    private String agvModel;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "warehouse_id")
    private Warehouse warehouse;

    @OneToMany(mappedBy = "agv")
    private List<AGVLog> logs = new ArrayList<>();
}
