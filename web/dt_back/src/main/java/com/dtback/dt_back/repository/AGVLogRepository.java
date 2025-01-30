package com.dtback.dt_back.repository;

import com.dtback.dt_back.entity.AGVLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AGVLogRepository extends JpaRepository<AGVLog, Integer> {
}
