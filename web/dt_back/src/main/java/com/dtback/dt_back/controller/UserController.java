package com.dtback.dt_back.controller;

import com.dtback.dt_back.dto.request.LoginRequestDto;
import com.dtback.dt_back.dto.request.SignupRequestDto;
import com.dtback.dt_back.dto.request.UpdateUserRequestDto;
import com.dtback.dt_back.dto.response.ApiResponse;
import com.dtback.dt_back.dto.response.WarehouseDto;
import com.dtback.dt_back.entity.User;
import com.dtback.dt_back.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;

    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/signup")
    public ResponseEntity<ApiResponse<User>> signup(@RequestBody SignupRequestDto signupRequestDto) {
        return ResponseEntity.ok(userService.signup(signupRequestDto));
    }

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<String>> login(@RequestBody LoginRequestDto loginRequestDto) {

        return ResponseEntity.ok(userService.login(loginRequestDto));
    }

    @PostMapping("/logout")
    public ResponseEntity<ApiResponse<String>> logout() {
        return ResponseEntity.ok(userService.logout());
    }

    @GetMapping("/current")
    public ResponseEntity<ApiResponse<User>> getCurrentUser() {
        return ResponseEntity.ok(userService.getCurrentUser());
    }

    @GetMapping("/warehouses/{companyId}")
    public ResponseEntity<ApiResponse<List<WarehouseDto>>> getWarehousesByCompany(
            @PathVariable Integer companyId) {
        return ResponseEntity.ok(userService.getWarehousesByCompany(companyId));
    }

    @GetMapping("/check-email")
    public ResponseEntity<ApiResponse<Boolean>> checkEmailDuplicate(@RequestParam String email) {
        return ResponseEntity.ok(userService.checkEmailDuplicate(email));
    }

    @PutMapping("/update")
    public ResponseEntity<ApiResponse<User>> updateUserInfo(@RequestBody UpdateUserRequestDto updateDto) {
        return ResponseEntity.ok(userService.updateUserInfo(updateDto));
    }
}
