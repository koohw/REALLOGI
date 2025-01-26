package com.dtback.dt_back.service;

import com.dtback.dt_back.entity.Company;
import com.dtback.dt_back.repository.CompanyRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;

@Service
@Transactional
public class CompanyService {
    private final CompanyRepository companyRepository;

    @Autowired
    public CompanyService(CompanyRepository companyRepository) {
        this.companyRepository = companyRepository;
    }

    public void saveCompany(Company company) {
        companyRepository.save(company);
    }
}