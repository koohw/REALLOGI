package com.dtback.dt_back.dto.request;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class SignupRequestDto {
    private String email;
    private String password;
    private String userName;
    private String phoneNumber;
    private Integer companyId;
    private Integer warehouseId;
    private String warehouseCode;
}
