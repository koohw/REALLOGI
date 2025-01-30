package com.dtback.dt_back.dto.response;

import com.dtback.dt_back.entity.Company;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class CompanyDto {
    private Integer companyId;
    private String companyName;

    public CompanyDto(Company company) {
        this.companyId = company.getCompanyId();
        this.companyName = company.getCompanyName();
    }
}
