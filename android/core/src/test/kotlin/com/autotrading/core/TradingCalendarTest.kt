package com.autotrading.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.LocalDate
import java.time.YearMonth

class TradingCalendarTest {
    private val calendar = TradingCalendar.bundled()

    @Test
    fun `내장 휴장일과 주말은 거래일이 아니다`() {
        assertFalse(calendar.isTradingDay(LocalDate.parse("2026-02-17"))) // 설날
        assertFalse(calendar.isTradingDay(LocalDate.parse("2026-10-03"))) // 토요일
        assertTrue(calendar.isTradingDay(LocalDate.parse("2026-10-06")))
    }

    @Test
    fun `월 첫 거래일은 휴장일과 주말을 건너뛴다`() {
        assertEquals(LocalDate.parse("2026-01-02"), calendar.firstTradingDay(YearMonth.of(2026, 1)))
        assertEquals(LocalDate.parse("2026-03-03"), calendar.firstTradingDay(YearMonth.of(2026, 3))) // 3/1 일, 3/2 대체
        assertEquals(LocalDate.parse("2026-11-02"), calendar.firstTradingDay(YearMonth.of(2026, 11))) // 11/1 일
    }

    @Test
    fun `월 마지막 거래일은 연말 휴장을 건너뛴다`() {
        assertEquals(LocalDate.parse("2026-12-30"), calendar.lastTradingDay(YearMonth.of(2026, 12)))
    }

    @Test
    fun `목록에 없는 해는 커버되지 않음을 알린다`() {
        assertTrue(calendar.isCovered(LocalDate.parse("2026-05-01")))
        assertFalse(calendar.isCovered(LocalDate.parse("2027-01-04")))
    }

    @Test
    fun `json에서 읽는다`() {
        val cal = TradingCalendar.fromJson("""{"years": {"2030": ["2030-01-01"]}}""")
        assertEquals(LocalDate.parse("2030-01-02"), cal.firstTradingDay(YearMonth.of(2030, 1)))
    }
}
