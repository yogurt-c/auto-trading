package com.autotrading.kis

import com.autotrading.core.Side
import okhttp3.mockwebserver.SocketPolicy
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant

private const val ORDER = """"output":{"KRX_FWDG_ORD_ORGNO":"06010","ODNO":"0001569157","ORD_TMD":"091000"}"""
private const val BUYING_POWER = """"output":{"ord_psbl_cash":"1000000","nrcvb_buy_amt":"990000"}"""

class KisHttpTest {
    private val tokens = InMemoryTokenStore()
    private val kis = KisFixture(tokens = tokens)

    @AfterEach
    fun close() = kis.close()

    @Test
    fun `토큰은 한 번 발급해 저장하고 이후 호출에 재사용한다`() {
        kis.enqueue(json(TOKEN_JSON), ok(BUYING_POWER), ok(BUYING_POWER))

        kis.client.buyingPower()
        kis.client.buyingPower()

        val issue = kis.take()
        assertEquals("/oauth2/tokenP", issue.path)
        assertTrue(issue.body.readUtf8().contains("\"grant_type\":\"client_credentials\""))
        repeat(2) {
            val api = kis.take()
            assertEquals("Bearer tok-1", api.getHeader("authorization"))
            assertEquals("app-key-123", api.getHeader("appkey"))
            assertEquals("VTTC8908R", api.getHeader("tr_id"))
            assertEquals("P", api.getHeader("custtype"))
        }
        assertEquals(3, kis.server.requestCount)
        assertEquals(Instant.parse("2026-11-03T00:10:00Z"), tokens.load()?.expiresAt)
    }

    @Test
    fun `저장된 토큰이 만료 10분 전이면 새로 발급한다`() {
        tokens.save(AccessToken("old", kis.time.now.plusSeconds(9 * 60)))
        kis.enqueue(json(TOKEN_JSON), ok(BUYING_POWER))

        kis.client.buyingPower()

        assertEquals("/oauth2/tokenP", kis.take().path)
        assertEquals("Bearer tok-1", kis.take().getHeader("authorization"))
    }

    @Test
    fun `만료된 토큰 응답이면 한 번 재발급하고 다시 보낸다`() {
        tokens.save(AccessToken("stale", kis.time.now.plusSeconds(3600)))
        kis.enqueue(kisError("EGW00123", "기간이 만료된 token 입니다."), json(TOKEN_JSON), ok(BUYING_POWER))

        assertEquals(990_000, kis.client.buyingPower())

        assertEquals("Bearer stale", kis.take().getHeader("authorization"))
        assertEquals("/oauth2/tokenP", kis.take().path)
        assertEquals("Bearer tok-1", kis.take().getHeader("authorization"))
    }

    @Test
    fun `새 토큰도 거부되면 인증 실패로 멈춘다`() {
        kis.enqueue(json(TOKEN_JSON), kisError("EGW00121", "유효하지 않은 token"))
        kis.enqueue(json(TOKEN_JSON), kisError("EGW00121", "유효하지 않은 token"))

        val e = assertThrows<KisException.Auth> { kis.client.buyingPower() }
        assertEquals("EGW00121", e.code)
        assertEquals(4, kis.server.requestCount)
    }

    @Test
    fun `토큰 발급 서버 오류는 인증 실패가 아니라 다시 시도한다 - 주문도 한 번만 보낸다`() {
        kis.enqueue(json("<html>Internal Server Error</html>", 500), json(TOKEN_JSON), ok(ORDER))

        kis.client.placeMarketOrder("069500", Side.SELL, 3)

        assertEquals(listOf("/oauth2/tokenP", "/oauth2/tokenP"), List(2) { kis.take().path })
        assertEquals("VTTC0011U", kis.take().getHeader("tr_id"))
        assertEquals(3, kis.server.requestCount)
    }

    @Test
    fun `토큰 발급 서버 오류가 계속되면 Transport`() {
        repeat(KisHttp.MAX_ATTEMPTS) { kis.enqueue(json("", 503)) }

        assertThrows<KisException.Transport> { kis.client.buyingPower() }
        assertEquals(KisHttp.MAX_ATTEMPTS, kis.server.requestCount)
    }

    @Test
    fun `토큰 발급 1분 제한이면 TokenIssueLimited`() {
        kis.enqueue(json("""{"error_code":"EGW00133","error_description":"접근토큰 발급 잠시 후 다시 시도하세요(1분당 1회)"}""", 403))

        assertThrows<KisException.TokenIssueLimited> { kis.client.buyingPower() }
    }

    @Test
    fun `호출 한도 초과는 기다렸다가 다시 보낸다`() {
        kis.enqueue(json(TOKEN_JSON), kisError("EGW00201", "초당 거래건수를 초과하였습니다."), ok(BUYING_POWER))

        assertEquals(990_000, kis.client.buyingPower())
        assertTrue(1_000L in kis.time.sleeps)
    }

    @Test
    fun `호출 한도 초과가 계속되면 RateLimited`() {
        kis.enqueue(json(TOKEN_JSON))
        repeat(KisHttp.MAX_ATTEMPTS) { kis.enqueue(kisError("EGW00201", "초당 거래건수를 초과하였습니다.")) }

        assertThrows<KisException.RateLimited> { kis.client.buyingPower() }
    }

    @Test
    fun `주문도 호출 한도 거부는 처리되지 않았으므로 다시 보낸다`() {
        kis.enqueue(
            json(TOKEN_JSON),
            kisError("EGW00201", "초당 거래건수를 초과하였습니다."),
            ok(""""output":{"KRX_FWDG_ORD_ORGNO":"06010","ODNO":"0001569157","ORD_TMD":"091000"}"""),
        )

        assertEquals("0001569157", kis.client.placeMarketOrder("069500", Side.BUY, 3).orderNo)
        assertEquals(3, kis.server.requestCount)
    }

    @Test
    fun `조회는 본문 없는 5xx면 재시도한다`() {
        kis.enqueue(json(TOKEN_JSON), json("Bad Gateway", 502), ok(BUYING_POWER))

        assertEquals(990_000, kis.client.buyingPower())
    }

    @Test
    fun `주문은 본문 없는 5xx면 재시도하지 않고 Transport — 접수 여부를 모른다`() {
        kis.enqueue(json(TOKEN_JSON), json("Bad Gateway", 502))

        assertThrows<KisException.Transport> { kis.client.placeMarketOrder("069500", Side.BUY, 3) }
        assertEquals(2, kis.server.requestCount)
    }

    @Test
    fun `주문 중 연결이 끊기면 재시도하지 않는다`() {
        kis.enqueue(json(TOKEN_JSON), json("").setSocketPolicy(SocketPolicy.DISCONNECT_AFTER_REQUEST))

        assertThrows<KisException.Transport> { kis.client.placeMarketOrder("069500", Side.SELL, 1) }
        assertEquals(2, kis.server.requestCount)
    }

    @Test
    fun `업무 거부는 응답코드와 메시지를 담고 재시도하지 않는다`() {
        kis.enqueue(json(TOKEN_JSON), kisError("40580000", "모의투자 장종료 입니다.", http = 200))

        val e = assertThrows<KisException.Rejected> { kis.client.placeMarketOrder("069500", Side.BUY, 3) }
        assertEquals("40580000", e.code)
        assertEquals("[40580000] 모의투자 장종료 입니다.", e.message)
        assertEquals(2, kis.server.requestCount)
    }

    @Test
    fun `연속 호출은 모의투자 최소 간격만큼 띄운다`() {
        kis.enqueue(json(TOKEN_JSON), ok(BUYING_POWER), ok(BUYING_POWER))

        kis.client.buyingPower()
        kis.client.buyingPower()

        assertEquals(List(2) { KisEnvironment.PAPER.minIntervalMillis }, kis.time.sleeps)
    }

    @Test
    fun `예외 메시지와 toString에 키·토큰·계좌번호가 없다`() {
        kis.enqueue(json(TOKEN_JSON), kisError("40580000", "모의투자 장종료 입니다.", http = 200))
        val e = assertThrows<KisException.Rejected> { kis.client.placeMarketOrder("069500", Side.BUY, 3) }

        val texts = listOf(
            e.message.orEmpty(),
            KisCredentials("app-key-123", "app-secret-456").toString(),
            AccessToken("tok-1", Instant.EPOCH).toString(),
            Account("50123456").toString(),
        )
        for (secret in listOf("app-key-123", "app-secret-456", "tok-1", "50123456")) {
            assertFalse(texts.any { secret in it }, secret)
        }
        assertEquals("50****56-01", Account.parse("50123456-01").masked)
    }
}
