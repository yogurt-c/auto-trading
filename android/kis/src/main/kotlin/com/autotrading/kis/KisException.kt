package com.autotrading.kis

/** 메시지에는 KIS 응답코드·응답메시지만 담는다. 키·토큰·계좌번호는 넣지 않는다. */
sealed class KisException(message: String, cause: Throwable? = null) : Exception(message, cause) {
    /** KIS가 요청을 처리하지 않고 거부했다 (rt_cd != 0). 주문이면 접수되지 않은 것이다. */
    class Rejected(val code: String, val kisMessage: String) : KisException("[$code] $kisMessage")

    /** 초당 호출 한도(EGW00201)를 재시도 후에도 넘었다. 처리되지 않았다. */
    class RateLimited : KisException("KIS 호출 한도 초과 (EGW00201)")

    /** 토큰 발급은 1분에 1회만 가능하다 (EGW00133). 1분 뒤 다시 시도한다. */
    class TokenIssueLimited : KisException("토큰 발급 제한 — 1분 뒤 다시 시도 (EGW00133)")

    /** 토큰 발급 실패 또는 새로 받은 토큰도 거부됨. 키를 다시 확인해야 한다. */
    class Auth(val code: String, kisMessage: String) : KisException("인증 실패 [$code] $kisMessage")

    /**
     * 네트워크 끊김·응답 없는 5xx. 조회는 재시도 후에도 실패한 것이다.
     * **주문·취소에서 나면 접수 여부를 알 수 없다** — 재주문하지 말고 주문체결조회로 확인한다.
     */
    class Transport(message: String, cause: Throwable? = null) : KisException(message, cause)

    /** 응답 형식이 예상과 다르다. */
    class Malformed(message: String) : KisException(message)
}
