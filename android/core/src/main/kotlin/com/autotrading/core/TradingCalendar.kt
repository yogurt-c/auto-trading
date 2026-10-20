package com.autotrading.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth

/**
 * KRX 거래일 달력. 휴장일 목록은 모의투자에서 휴장일 API(CTCA0903R)를 쓸 수 없어 앱에 내장한다.
 * 목록에 없는 해([coveredYears] 밖)는 주말만 빼고 거래일로 보며, 실행 시점에 시세로 다시 확인해야 한다.
 */
class TradingCalendar(private val holidays: Set<LocalDate>, val coveredYears: Set<Int>) {
    fun isCovered(date: LocalDate): Boolean = date.year in coveredYears

    fun isTradingDay(date: LocalDate): Boolean =
        date.dayOfWeek != DayOfWeek.SATURDAY && date.dayOfWeek != DayOfWeek.SUNDAY && date !in holidays

    fun nextTradingDay(after: LocalDate): LocalDate =
        generateSequence(after.plusDays(1)) { it.plusDays(1) }.first(::isTradingDay)

    fun firstTradingDay(month: YearMonth): LocalDate =
        if (isTradingDay(month.atDay(1))) month.atDay(1) else nextTradingDay(month.atDay(1))

    fun lastTradingDay(month: YearMonth): LocalDate =
        generateSequence(month.atEndOfMonth()) { it.minusDays(1) }.first(::isTradingDay)

    @Serializable
    private data class HolidayFile(val years: Map<String, List<String>>)

    companion object {
        private const val RESOURCE = "/krx_holidays.json"
        private val JSON = Json { ignoreUnknownKeys = true } // "_source" 설명 필드

        fun fromJson(json: String): TradingCalendar {
            val file = JSON.decodeFromString<HolidayFile>(json)
            return TradingCalendar(
                holidays = file.years.values.flatten().map(LocalDate::parse).toSet(),
                coveredYears = file.years.keys.map(String::toInt).toSet(),
            )
        }

        fun bundled(): TradingCalendar {
            val text = requireNotNull(TradingCalendar::class.java.getResource(RESOURCE)) { "$RESOURCE 없음" }.readText()
            return fromJson(text)
        }
    }
}
