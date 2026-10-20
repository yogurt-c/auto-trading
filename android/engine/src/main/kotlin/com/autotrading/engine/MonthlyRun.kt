package com.autotrading.engine

import com.autotrading.core.OrderIntent
import com.autotrading.core.Profile
import com.autotrading.core.Side
import kotlinx.serialization.KSerializer
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.json.Json
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth

/** 설계 문서 4절의 상태. 새 주문을 보내기 전 단계에서만 날짜가 바뀌어도 안전하게 다시 계획할 수 있다. */
enum class RunState { SCHEDULED, CHECKED_OPEN, PLANNED, SELLS_SENT, SELLS_SETTLED, BUYS_SENT, DONE, FAILED }

/**
 * 보낸(또는 보내는 중인) 주문 1건. [orderNo]가 null이면 전송 결과를 모른다 —
 * 다음 실행 때 주문체결조회로 접수 여부를 확인하기 전에는 같은 주문을 다시 보내지 않는다.
 */
@Serializable
data class OrderRecord(
    @Serializable(LocalDateSerializer::class) val date: LocalDate,
    val code: String,
    val side: Side,
    val qty: Int,
    val limitPrice: Long? = null,
    val orderNo: String? = null,
    val orgNo: String = "",
    val filledQty: Int = 0,
    val avgPrice: Double = 0.0,
    val open: Boolean = true,
)

@Serializable
data class PlannedOrder(val code: String, val side: Side, val qty: Int, val limitPrice: Long? = null) {
    constructor(intent: OrderIntent, limitPrice: Long? = null) : this(intent.code, intent.side, intent.qty, limitPrice)
}

/** `run_key = YYYY-MM` 당 1건. 단계마다 [RunStore]에 저장해 앱이 죽어도 이어서 진행한다. */
@Serializable
data class MonthlyRun(
    @Serializable(YearMonthSerializer::class) val month: YearMonth,
    val profile: Profile,
    val state: RunState = RunState.SCHEDULED,
    @Serializable(LocalDateSerializer::class) val tradeDate: LocalDate? = null,
    val prevClose: Map<String, Double> = emptyMap(),
    val equity: Double = 0.0,
    val targets: Map<String, Int> = emptyMap(),
    val plannedSells: List<PlannedOrder>? = null,
    val plannedBuys: List<PlannedOrder>? = null,
    val orders: List<OrderRecord> = emptyList(),
    @Serializable(InstantSerializer::class) val phaseStartedAt: Instant? = null,
    val failure: String? = null,
) {
    val isFinished: Boolean get() = state == RunState.DONE || state == RunState.FAILED

    fun toJson(): String = JSON.encodeToString(serializer(), this)

    companion object {
        private val JSON = Json { ignoreUnknownKeys = true }

        fun fromJson(text: String): MonthlyRun = JSON.decodeFromString(serializer(), text)
    }
}

/** app은 Room으로 구현한다 (month → [MonthlyRun.toJson]). */
interface RunStore {
    fun load(month: YearMonth): MonthlyRun?
    fun save(run: MonthlyRun)
}

class InMemoryRunStore : RunStore {
    private val runs = mutableMapOf<YearMonth, String>()

    @Synchronized
    override fun load(month: YearMonth) = runs[month]?.let(MonthlyRun::fromJson)

    @Synchronized
    override fun save(run: MonthlyRun) {
        runs[run.month] = run.toJson()
    }
}

internal abstract class StringSerializer<T>(name: String, private val parse: (String) -> T) : KSerializer<T> {
    override val descriptor = PrimitiveSerialDescriptor(name, PrimitiveKind.STRING)
    override fun serialize(encoder: Encoder, value: T) = encoder.encodeString(value.toString())
    override fun deserialize(decoder: Decoder): T = parse(decoder.decodeString())
}

internal object LocalDateSerializer : StringSerializer<LocalDate>("LocalDate", LocalDate::parse)
internal object YearMonthSerializer : StringSerializer<YearMonth>("YearMonth", YearMonth::parse)
internal object InstantSerializer : StringSerializer<Instant>("Instant", Instant::parse)
