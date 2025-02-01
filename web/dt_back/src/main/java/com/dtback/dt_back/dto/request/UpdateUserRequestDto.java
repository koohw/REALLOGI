package com.dtback.dt_back.dto.request;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class UpdateUserRequestDto {

    private String currentPassword;
    private String newPassword;
    private String userName;
    private String phoneNumber;

    // Getters and Setters
}
