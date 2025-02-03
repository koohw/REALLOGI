package com.dtback.dt_back.service;

import com.dtback.dt_back.entity.AGV;
import com.dtback.dt_back.repository.AGVRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional
public class AGVService {
    private final AGVRepository agvRepository;

    @Autowired
    public AGVService(AGVRepository agvRepository) {
        this.agvRepository = agvRepository;
    }

    // AGV 등록
    public AGV createAgv(AGV agv) {
        return agvRepository.save(agv);
    }

    // AGV 조회
    public List<AGV> getAllAgvs() {
        return agvRepository.findAll();
    }

    // AGV 단건 조회
    public AGV getAgvById(int id) {
        return agvRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("AGV not found"));
    }

    // AGV 수정
    public AGV updateAgv(AGV agv) {
        return agvRepository.save(agv);
    }

    // AGV 삭제
    public void deleteAgv(int id) {
        agvRepository.deleteById(id);
    }
}
