package com.dtback.dt_back.config;

import lombok.Getter;

/**
 * 에러 코드 관리
 */
@Getter
public enum BaseResponseStatus {
    /**
     * 1000 : 요청 성공
     */
    SUCCESS(true, 1000, "요청에 성공하였습니다."),


    /**
     * 2000 : Request 오류
     */
    // Common
    REQUEST_ERROR(false, 2000, "입력값을 확인해주세요."),
    EMPTY_JWT(false, 2001, "JWT를 입력해주세요."),
    INVALID_JWT(false, 2002, "유효하지 않은 JWT입니다."),
    INVALID_USER_JWT(false,2003,"권한이 없는 유저의 접근입니다."),

    // users
    USERS_EMPTY_USER_ID(false, 2010, "유저 아이디 값을 확인해주세요."),

    // [POST] /users
    POST_USERS_EMPTY_EMAIL(false, 2015, "이메일을 입력해주세요."),
    POST_USERS_INVALID_EMAIL(false, 2016, "이메일 형식을 확인해주세요."),
    POST_USERS_EXISTS_EMAIL(false,2017,"중복된 이메일입니다."),
    POST_USERS_EMPTY_NAME(false, 2018, "성명을 입력해 주세요."),
    POST_USERS_EMPTY_NICKNAME(false, 2019, "닉네임을 입력해 주세요."),
    POST_USERS_EMPTY_PASSWORD(false, 2020, "비밀번호를 입력해 주세요."),
    POST_USERS_EMPTY_LOGINID(false, 2021, "로그인 아이디를 입력해 주세요."),
    POST_USERS_EXISTS_LOGINID(false, 2022,"중복된 아이디 입니다."),
    POST_USERS_EMPTY_PHONENUMBER(false, 2023,"휴대전화 번호를 입력해 주세요."),
    POST_USERS_EXISTS_PHONENUMBER(false, 2041,"이미 존재하는 전화번호 입니다"),
    POST_USERS_EMPTY_VERIFYNUMBER(false,2024,"인증번호를 입력해 주세요."),
    POST_USERS_EXISTS_BOOKMARK(false,2027,"이미 존재하는 북마크 입니다"),
    POST_USERS_EXISTS_NON_EXIST_RECIPE(false,2033," 존재하지 않는 레시피 입니다"),
    POST_USERS_EXISTS_REPORT(false,2034,"이미 신고한 게시물 입니다"),
    POST_USERS_EXISTS_PHONENUMBER_AND_EMAIL(false, 2040,"이미 존재하는 이메일과 휴대번호입니다."),

    // POST /products
    POST_PRODUCTS_EMPTY_PRODUCTID(false,2025,"상품ID를 입력해 주세요."),
    POST_PRODUCTS_EMPTY_RECIPEID(false,2031,"레시피ID를 입력해 주세요."),
    POST_PRODUCTS_EMPTY_REVIEWIDX(false,2035,"리뷰ID를 입력해 주세요."),
    POST_PRODUCTS_EMPTY_USERID(false,2026,"유저ID를 입력해 주세요."),
    POST_REVIEWS_DISABLE(false,2027,"리뷰를 쓸 자격이 없습니다."),
    POST_INPUT_SEARCH(false,2028,"검색어를 입력해 주세요"),
    POST_INPUT_CATEGORY(false,2036,"카테고리를 입력해 주세요"),

    POST_RECIPE_DETAILS(false,2029,"레시피 세부사항이 비었습니다."),

    POST_RECIPE_ID(false,2030,"레시피 아이디를 입력하시오."),
    POST_TARGET_ID(false,2042,"신고 대상 게시물 및 리뷰 id를 입력하시오."),
    POST_REVIEWS_EXIST(false,2032,"이미 리뷰를 작성했습니다."),
    POST_USERS_SELF_REPORT(false,2044,"자기 자신을 신고할 수 없습니다."),






    /**
     * 3000 : Response 오류
     */
    // Common
    RESPONSE_ERROR(false, 3000, "값을 불러오는데 실패하였습니다."),

    // [POST] /users
    DUPLICATED_EMAIL(false, 3013, "중복된 이메일입니다."),
    FAILED_TO_LOGIN(false,3014,"없는 아이디거나 비밀번호가 틀렸습니다."),
    VERIFY_FAIL(false,3015,"인증에 실패하였습니다."),

    INSERT_FAIL_POSTBOOKMARK(false,3016,"찜 추가 실패"),
    INSERT_FAIL_CART(false,3017,"장바구니 실패"),
    INSERT_FAIL_REVIEW(false,3018,"리뷰 추가 실패"),
    DISABLED_USER(false,3019,"회원탈퇴한 계정"),
    WRONG_PASSWORD(false,3020,"비밀번호가 틀렸습니다"),
    INSERT_FAIL_REPORT(false,3021,"신고 실패"),
    FAILED_TO_CHECKEMAIL_OR_PHONENUMBER(false,3022,"이메일과 전화번호가 일치하지 않거나 존재하지 않습니다."),





    /**
     * 4000 : Database, Server 오류
     */
    DATABASE_ERROR(false, 4000, "데이터베이스 연결에 실패하였습니다."),
    SERVER_ERROR(false, 4001, "서버와의 연결에 실패하였습니다."),
    TEST_ERROR1(false,4002,"문제점 위치 파악 에러"),
    TEST_ERROR2(false,4003,"문제점 위치 파악 에러"),
    TEST_ERROR3(false,4004,"문제점 위치 파악 에러"),
    TEST_ERROR4(false,4005,"문제점 위치 파악 에러"),

    //[PATCH] /users/{userIdx}
    MODIFY_FAIL_USERNAME(false,4014,"유저네임 수정 실패"),

    MODIFY_FAIL_REVIEW(false,4017,"리뷰 수정 실패"),

    MODIFY_FAIL_BOOKMARK(false,4015,"북마크 해제 실패"),

    MODIFY_FAIL_USERSTATUS(false,4016,"회원탈퇴 실패"),
    MODIFY_FAIL_USERSTOKEN(false,4022,"로그아웃 실패"),
    MODIFY_FAIL_USERSINFOTATUS(false,4018,"회원정보 수정 실패"),
    MODIFY_FAIL_USERPISTATUS(false,4019,"회원프로필 수정 실패"),

    DELETE_FAIL_RECIPE(false,4020,"레시피 삭제 실패"),



    PASSWORD_ENCRYPTION_ERROR(false, 4011, "비밀번호 암호화에 실패하였습니다."),
    PASSWORD_DECRYPTION_ERROR(false, 4012, "비밀번호 복호화에 실패하였습니다."),
    REFRESH_TOKEN_NOT_EXIST(false  ,4023    ,"refresh 토큰이 일치하지 않거나 기한이 만료되었습니다." ),
    FAIL_CHEKCK_ACCESSTOKEN(false  ,4024    ,"Acess 토큰이 일치하지 않거나 기한이 만료되었습니다." ),
    TOKEN_NOT_EXIST(false  ,4025    ,"토큰이 존재하지 않습니다"  ),
    INVALID_REFRESH_TOKEN(false,4026 ,"유효하지 않는 토큰입니다." ),
    MISMATCH_REFRESH_TOKEN(false,4027 ,"refresh 토큰이 유효한 토큰이 아닙니다." ),
    FAIL_TO_CHANGE_PASSWORD(false,4028 ,"임시 비밀번호 변경에 실패했습니다."),
    PERPLEXITY_API_ERROR(false,4029,"Perplexity API를 불러오지 못했습니다.");





    // 5000 : 필요시 만들어서 쓰세요

    // 6000 : 필요시 만들어서 쓰세요


    private final boolean isSuccess;
    private final int code;
    private final String message;

    private BaseResponseStatus(boolean isSuccess, int code, String message) {
        this.isSuccess = isSuccess;
        this.code = code;
        this.message = message;
    }
}
