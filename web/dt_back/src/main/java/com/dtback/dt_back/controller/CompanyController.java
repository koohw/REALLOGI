package com.dtback.dt_back.controller;

import com.dtback.dt_back.dto.response.ApiResponse;
import com.dtback.dt_back.dto.response.CompanyDto;
import com.dtback.dt_back.service.CompanyService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/companies")
public class CompanyController {
    private final CompanyService companyService;

    public CompanyController(CompanyService companyService) {
        this.companyService = companyService;
    }
    @GetMapping
    public ResponseEntity<ApiResponse<List<CompanyDto>>> getAllCompanies() {
        return ResponseEntity.ok(companyService.getAllCompanies());
    }
}
