package com.dtback.dt_back.service;

import com.dtback.dt_back.dto.response.ApiResponse;
import com.dtback.dt_back.dto.response.CompanyDto;
import com.dtback.dt_back.entity.Company;
import com.dtback.dt_back.repository.CompanyRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.stream.Collectors;

@Service
@Transactional
public class CompanyService {
    private final CompanyRepository companyRepository;

    @Autowired
    public CompanyService(CompanyRepository companyRepository) {
        this.companyRepository = companyRepository;
    }

    public ApiResponse<List<CompanyDto>> getAllCompanies() {
        List<Company> companies = companyRepository.findAll();
        List<CompanyDto> companyDtos = companies.stream()
                .map(CompanyDto::new)
                .collect(Collectors.toList());

        return new ApiResponse<>(true, "Companies retrieved successfully", companyDtos);
    }

    public void saveCompany(Company company) {
        companyRepository.save(company);
    }
}