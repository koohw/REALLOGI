package com.dtback.dt_back.controller;

import com.dtback.dt_back.config.BaseResponse;
import com.dtback.dt_back.config.BaseResponseStatus;
import com.dtback.dt_back.entity.AGV;
import com.dtback.dt_back.service.AGVService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/agvs")
public class AgvController {

    private final AGVService agvService;

    @Autowired
    public AgvController(AGVService agvService) {
        this.agvService = agvService;
    }
    @PostMapping("/register")
    public BaseResponse<AGV> createAgv(@RequestBody AGV agv) {
        try {
            AGV createdAgv = agvService.createAgv(agv);

            return new BaseResponse<>(createdAgv);
        } catch (Exception e) {
            return new BaseResponse<>(BaseResponseStatus.DATABASE_ERROR);
        }
    }

    @GetMapping("/allAgvs")
    public BaseResponse<List<AGV>> getAllAgvs() {
        try {
            List<AGV> agvList = agvService.getAllAgvs();
            return new BaseResponse<>(agvList);
        } catch (Exception e) {
            return new BaseResponse<>(BaseResponseStatus.DATABASE_ERROR);
        }
    }

    @GetMapping("/search/{id}")
    public BaseResponse<AGV> getAgv(@PathVariable int id) {
        try {
            AGV agv = agvService.getAgvById(id);
            return new BaseResponse<>(agv);
        } catch (Exception e) {
            return new BaseResponse<>(BaseResponseStatus.DATABASE_ERROR);
        }
    }

    @PutMapping("/edit/{id}")
    public BaseResponse<AGV> updateAgv(@PathVariable int id, @RequestBody AGV agv) {
        try {
            agv.setAgvId(id);
            AGV updatedAgv = agvService.updateAgv(agv);
            return new BaseResponse<>(updatedAgv);
        } catch (Exception e) {
            return new BaseResponse<>(BaseResponseStatus.DATABASE_ERROR);
        }
    }

    @DeleteMapping("/del/{id}")
    public BaseResponse<String> deleteAgv(@PathVariable int id) {
        try {
            agvService.deleteAgv(id);
            return new BaseResponse<>("AGV successfully deleted");
        } catch (Exception e) {
            return new BaseResponse<>(BaseResponseStatus.DATABASE_ERROR);
        }
    }
}



