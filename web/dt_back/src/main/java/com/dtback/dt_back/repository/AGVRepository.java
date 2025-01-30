package com.dtback.dt_back.repository;

import com.dtback.dt_back.entity.AGV;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AGVRepository extends JpaRepository<AGV, Integer> {
}
