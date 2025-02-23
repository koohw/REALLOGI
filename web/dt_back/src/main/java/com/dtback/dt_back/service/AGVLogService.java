package com.dtback.dt_back.service;

import com.dtback.dt_back.repository.AGVLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class AGVLogService {
    private final AGVLogRepository agvLogRepository;

    @Autowired
    public AGVLogService(AGVLogRepository agvLogRepository) {
        this.agvLogRepository = agvLogRepository;
    }


}
