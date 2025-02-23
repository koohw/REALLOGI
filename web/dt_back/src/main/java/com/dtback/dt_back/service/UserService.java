package com.dtback.dt_back.service;

import com.dtback.dt_back.dto.request.LoginRequestDto;
import com.dtback.dt_back.dto.request.SignupRequestDto;
import com.dtback.dt_back.dto.request.UpdateUserRequestDto;
import com.dtback.dt_back.dto.response.ApiResponse;
import com.dtback.dt_back.dto.response.WarehouseDto;
import com.dtback.dt_back.entity.Company;
import com.dtback.dt_back.entity.User;
import com.dtback.dt_back.entity.Warehouse;
import com.dtback.dt_back.repository.CompanyRepository;
import com.dtback.dt_back.repository.UserRepository;
import com.dtback.dt_back.repository.WarehouseRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@Transactional
public class UserService {
    private final UserRepository userRepository;
    private final CompanyRepository companyRepository;
    private final WarehouseRepository warehouseRepository;
    private final HttpSession httpSession;

    @Autowired
    public UserService(UserRepository userRepository,
                       CompanyRepository companyRepository,
                       WarehouseRepository warehouseRepository,
                       HttpSession httpSession) {
        this.userRepository = userRepository;
        this.companyRepository = companyRepository;
        this.warehouseRepository = warehouseRepository;
        this.httpSession = httpSession;
    }

    public ApiResponse<User> signup(SignupRequestDto signupRequestDto) {
        // 이메일 중복 체크
        if (userRepository.findByEmail(signupRequestDto.getEmail()).isPresent()) {
            throw new IllegalArgumentException("Email already exists");
        }

        // 회사 존재 확인
        Company company = companyRepository.findById(signupRequestDto.getCompanyId())
                .orElseThrow(() -> new IllegalArgumentException("Invalid company"));

        // 창고 존재 확인 및 회사 소속 확인
        Warehouse warehouse = warehouseRepository.findById(signupRequestDto.getWarehouseId())
                .orElseThrow(() -> new IllegalArgumentException("Invalid warehouse"));

        if (!warehouse.getCompanyId().equals(company.getCompanyId())) {
            throw new IllegalArgumentException("Warehouse does not belong to the selected company");
        }

        // 창고 코드 확인
        if (!warehouse.getWarehouseCode().equals(signupRequestDto.getWarehouseCode())) {
            throw new IllegalArgumentException("Invalid warehouse code");
        }

        // 새 사용자 생성 - userId는 제외하고 설정
        /*
        User newUser = User.builder()  // User 클래스에 @Builder 추가 필요
                .email(signupRequestDto.getEmail())
                .password(signupRequestDto.getPassword())
                .userName(signupRequestDto.getUserName())
                .phoneNumber(signupRequestDto.getPhoneNumber())
                .warehouseId(warehouse.getWarehouseId())
                .build();
        */
        // 또는 Builder를 사용하지 않는 경우:

        User newUser = new User();
        newUser.setEmail(signupRequestDto.getEmail());
        newUser.setPassword(signupRequestDto.getPassword());
        newUser.setUserName(signupRequestDto.getUserName());
        newUser.setPhoneNumber(signupRequestDto.getPhoneNumber());
        newUser.setWarehouseId(warehouse.getWarehouseId());


        User savedUser = userRepository.save(newUser);
        return new ApiResponse<>(true, "Signup successful", savedUser);
    }

    public ApiResponse<String> login(LoginRequestDto loginRequestDto) {
        Optional<User> userOptional = userRepository.findByEmail(loginRequestDto.getEmail());
        User user = userOptional.orElseThrow(() -> new IllegalArgumentException("Invalid email"));

        if (!user.getPassword().equals(loginRequestDto.getPassword())) {
            throw new IllegalArgumentException("Invalid password");
        }

        httpSession.setAttribute("USER", user);
        return new ApiResponse<>(true, "Login successful", null);
    }

    public ApiResponse<String> logout() {
        httpSession.invalidate();
        return new ApiResponse<>(true, "Logout successful", null);
    }

    public ApiResponse<User> getCurrentUser() {
        User user = (User) httpSession.getAttribute("USER");
        if (user == null) {
            return new ApiResponse<>(false, "Not logged in", null);
        }
        return new ApiResponse<>(true, "Current user retrieved", user);
    }

    // 회사별 창고 목록 조회
    public ApiResponse<List<WarehouseDto>> getWarehousesByCompany(Integer companyId) {
        List<Warehouse> warehouses = warehouseRepository.findByCompanyId(companyId);
        List<WarehouseDto> warehouseDtos = warehouses.stream()
                .map(w -> {
                    WarehouseDto dto = new WarehouseDto();
                    dto.setWarehouseId(w.getWarehouseId());
                    dto.setWarehouseName(w.getWarehouseName());
                    return dto;
                })
                .collect(Collectors.toList());

        return new ApiResponse<>(true, "Warehouses retrieved", warehouseDtos);
    }

    public ApiResponse<Boolean> checkEmailDuplicate(String email) {
        boolean exists = userRepository.findByEmail(email).isPresent();
        if (exists) {
            return new ApiResponse<>(false, "Email already exists", true);
        }
        return new ApiResponse<>(true, "Email is available", false);
    }

    public ApiResponse<User> updateUserInfo(UpdateUserRequestDto updateDto) {
        User currentUser = (User) httpSession.getAttribute("USER");
        if (currentUser == null) {
            throw new IllegalStateException("User not logged in");
        }

        if (!currentUser.getPassword().equals(updateDto.getCurrentPassword())) {
            throw new IllegalArgumentException("Current password is incorrect");
        }

        if (updateDto.getNewPassword() != null && !updateDto.getNewPassword().isEmpty()) {
            currentUser.setPassword(updateDto.getNewPassword());
        }

        if (updateDto.getUserName() != null && !updateDto.getUserName().isEmpty()) {
            currentUser.setUserName(updateDto.getUserName());
        }

        if (updateDto.getPhoneNumber() != null) {
            currentUser.setPhoneNumber(updateDto.getPhoneNumber());
        }

        User updatedUser = userRepository.save(currentUser);
        httpSession.setAttribute("USER", updatedUser);

        return new ApiResponse<>(
                true,
                "User information updated successfully",
                updatedUser
        );
    }
}
