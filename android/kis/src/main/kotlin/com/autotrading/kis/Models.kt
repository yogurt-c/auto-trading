package com.autotrading.kis

import com.autotrading.core.Side
import java.time.LocalDate

/** 보유 종목. 매도 수량은 [orderableQty]를 넘을 수 없다. */
data class Position(val code: String, val qty: Int, val orderableQty: Int)

/** [depositD2]: D+2 예수금 — 미결제 매매를 반영한 현금. 리밸런싱 총자산 계산에 쓴다. */
data class Balance(val positions: List<Position>, val depositD2: Long)

data class DailyBar(val date: LocalDate, val close: Long)

/** 주문 접수 결과. 취소에 [orgNo]가 필요하므로 주문번호와 함께 저장한다. */
data class OrderReceipt(val orderNo: String, val orgNo: String, val code: String, val side: Side, val qty: Int)

/**
 * 주식일별주문체결조회 한 줄. 취소 주문도 별도 줄로 나오며 [originalOrderNo]가 원주문번호다.
 * 미체결 수량 = 주문 - 체결 - 취소확인 - 거부.
 */
data class OrderStatus(
    val orderNo: String,
    val originalOrderNo: String?,
    val code: String,
    val side: Side,
    val orderedQty: Int,
    val filledQty: Int,
    val canceledQty: Int,
    val rejectedQty: Int,
    val avgPrice: Double,
) {
    val openQty: Int get() = (orderedQty - filledQty - canceledQty - rejectedQty).coerceAtLeast(0)
    val isSettled: Boolean get() = openQty == 0
}
