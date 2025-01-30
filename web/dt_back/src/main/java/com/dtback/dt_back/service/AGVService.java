package com.dtback.dt_back.service;

import com.dtback.dt_back.repository.AGVRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class AGVService {
    private final AGVRepository agvRepository;

    @Autowired
    public AGVService(AGVRepository agvRepository) {
        this.agvRepository = agvRepository;
    }
}
