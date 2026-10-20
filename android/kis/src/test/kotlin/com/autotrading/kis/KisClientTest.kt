package com.autotrading.kis

import com.autotrading.core.Side
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.LocalDate

class KisClientTest {
    private val tokens = InMemoryTokenStore()
    private val kis = KisFixture(tokens = tokens)

    @BeforeEach
    fun token() = kis.enqueue(json(TOKEN_JSON))

    @AfterEach
    fun close() = kis.close()

    @Test
    fun `잔고는 연속조회로 모든 페이지를 모으고 0주 종목은 뺀다`() {
        kis.enqueue(
            json(
                """{"rt_cd":"0","msg_cd":"","msg1":"","ctx_area_fk100":"FK1","ctx_area_nk100":"NK1",
                "output1":[{"pdno":"005930","hldg_qty":"10","ord_psbl_qty":"10"},
                           {"pdno":"114260","hldg_qty":"0","ord_psbl_qty":"0"}],
                "output2":[{"dnca_tot_amt":"500000","prvs_rcdl_excc_amt":"480000"}]}""",
                trCont = "M",
            ),
            json(
                """{"rt_cd":"0","msg_cd":"","msg1":"","ctx_area_fk100":"","ctx_area_nk100":"",
                "output1":[{"pdno":"069500","hldg_qty":"12","ord_psbl_qty":"7"}],
                "output2":[{"dnca_tot_amt":"500000","prvs_rcdl_excc_amt":"480000"}]}""",
                trCont = "D",
            ),
        )

        val balance = kis.client.balance()

        assertEquals(listOf(Position("005930", 10, 10), Position("069500", 12, 7)), balance.positions)
        assertEquals(480_000, balance.depositD2)
        val first = kis.takeApi()
        assertEquals("VTTC8434R", first.getHeader("tr_id"))
        assertEquals("50123456", first.requestUrl?.queryParameter("CANO"))
        assertEquals("", first.getHeader("tr_cont"))
        val second = kis.takeApi()
        assertEquals("N", second.getHeader("tr_cont"))
        assertEquals("FK1", second.requestUrl?.queryParameter("CTX_AREA_FK100"))
        assertEquals("NK1", second.requestUrl?.queryParameter("CTX_AREA_NK100"))
    }

    @Test
    fun `매수가능금액은 미수 없는 매수금액`() {
        kis.enqueue(ok(""""output":{"ord_psbl_cash":"1000000","nrcvb_buy_amt":"990000","max_buy_amt":"2400000"}"""))

        assertEquals(990_000, kis.client.buyingPower())
        val request = kis.takeApi()
        assertEquals("/uapi/domestic-stock/v1/trading/inquire-psbl-order", request.requestUrl?.encodedPath)
        assertEquals("01", request.requestUrl?.queryParameter("ORD_DVSN"))
    }

    @Test
    fun `일자별 시세는 최신 날짜 먼저`() {
        kis.enqueue(
            ok(
                """"output":[{"stck_bsop_date":"20261030","stck_clpr":"35215"},
                            {"stck_bsop_date":"20261102","stck_clpr":"35400"},
                            {"stck_bsop_date":"","stck_clpr":""}]""",
            ),
        )

        val bars = kis.client.dailyBars("069500")

        assertEquals(
            listOf(DailyBar(LocalDate.of(2026, 11, 2), 35_400), DailyBar(LocalDate.of(2026, 10, 30), 35_215)),
            bars,
        )
        val request = kis.takeApi()
        assertEquals("FHKST01010400", request.getHeader("tr_id"))
        assertEquals("069500", request.requestUrl?.queryParameter("FID_INPUT_ISCD"))
    }

    @Test
    fun `시장가 주문은 대문자 키와 매수·매도별 TR로 보낸다`() {
        kis.enqueue(
            ok(""""output":{"KRX_FWDG_ORD_ORGNO":"06010","ODNO":"0001569157","ORD_TMD":"091000"}"""),
            ok(""""output":{"KRX_FWDG_ORD_ORGNO":"06010","ODNO":"0001569158","ORD_TMD":"091001"}"""),
        )

        val sell = kis.client.placeMarketOrder("114260", Side.SELL, 4)
        val buy = kis.client.placeMarketOrder("069500", Side.BUY, 3)

        assertEquals(OrderReceipt("0001569157", "06010", "114260", Side.SELL, 4), sell)
        assertEquals("0001569158", buy.orderNo)
        val sellRequest = kis.takeApi()
        assertEquals("VTTC0011U", sellRequest.getHeader("tr_id"))
        val body = sellRequest.body.readUtf8()
        for (field in listOf(""""PDNO":"114260"""", """"ORD_DVSN":"01"""", """"ORD_QTY":"4"""", """"ORD_UNPR":"0"""")) {
            assertTrue(field in body, field)
        }
        assertEquals("VTTC0012U", kis.takeApi().getHeader("tr_id"))
    }

    @Test
    fun `잘못된 종목코드·수량은 보내기 전에 막는다`() {
        assertThrows<IllegalArgumentException> { kis.client.placeMarketOrder("69500", Side.BUY, 1) }
        assertThrows<IllegalArgumentException> { kis.client.placeMarketOrder("069500", Side.BUY, 0) }
        assertEquals(0, kis.server.requestCount)
    }

    @Test
    fun `주문체결조회는 체결·취소·거부 수량으로 미체결을 계산한다`() {
        kis.enqueue(
            ok(
                """"ctx_area_fk100":"","ctx_area_nk100":"","output1":[
                {"odno":"0000000001","orgn_odno":"","pdno":"114260","sll_buy_dvsn_cd":"01","ord_qty":"4",
                 "tot_ccld_qty":"4","cnc_cfrm_qty":"0","rjct_qty":"0","avg_prvs":"113405.0000"},
                {"odno":"0000000002","orgn_odno":"","pdno":"069500","sll_buy_dvsn_cd":"02","ord_qty":"10",
                 "tot_ccld_qty":"6","cnc_cfrm_qty":"0","rjct_qty":"0","avg_prvs":"35300"},
                {"odno":"0000000003","orgn_odno":"0000000002","pdno":"069500","sll_buy_dvsn_cd":"02","ord_qty":"4",
                 "tot_ccld_qty":"0","cnc_cfrm_qty":"4","rjct_qty":"0","avg_prvs":"0"}],
                "output2":{"tot_ord_qty":"18"}""",
            ),
        )

        val orders = kis.client.orders(LocalDate.of(2026, 11, 2))

        val (sold, partial, cancel) = orders
        assertTrue(sold.isSettled)
        assertEquals(113_405.0, sold.avgPrice)
        assertNull(sold.originalOrderNo)
        assertFalse(partial.isSettled)
        assertEquals(4, partial.openQty)
        assertEquals(Side.BUY, partial.side)
        assertEquals("0000000002", cancel.originalOrderNo)
        val request = kis.takeApi()
        assertEquals("VTTC0081R", request.getHeader("tr_id"))
        assertEquals("20261102", request.requestUrl?.queryParameter("INQR_STRT_DT"))
        assertEquals("20261102", request.requestUrl?.queryParameter("INQR_END_DT"))
    }

    @Test
    fun `취소는 원주문번호와 조직번호로 잔량 전부를 취소한다`() {
        kis.enqueue(ok(""""output":{"KRX_FWDG_ORD_ORGNO":"06010","ODNO":"0000000003","ORD_TMD":"094000"}"""))

        val cancelNo = kis.client.cancel(OrderReceipt("0000000002", "06010", "069500", Side.BUY, 10))

        assertEquals("0000000003", cancelNo)
        val request = kis.takeApi()
        assertEquals("VTTC0013U", request.getHeader("tr_id"))
        val body = request.body.readUtf8()
        for (field in listOf(
            """"ORGN_ODNO":"0000000002"""",
            """"KRX_FWDG_ORD_ORGNO":"06010"""",
            """"RVSE_CNCL_DVSN_CD":"02"""",
            """"QTY_ALL_ORD_YN":"Y"""",
        )) {
            assertTrue(field in body, field)
        }
    }

    @Test
    fun `숫자가 아닌 수량은 Malformed`() {
        kis.enqueue(
            ok(
                """"output1":[{"pdno":"069500","hldg_qty":"abc","ord_psbl_qty":"0"}],
                "output2":[{"prvs_rcdl_excc_amt":"0"}]""",
            ),
        )

        assertThrows<KisException.Malformed> { kis.client.balance() }
    }

    @Test
    fun `실전 환경은 실전 TR을 쓴다`() {
        KisFixture(env = KisEnvironment.REAL).use { real ->
            real.enqueue(json(TOKEN_JSON), ok(""""output":{"nrcvb_buy_amt":"1"}"""))
            real.client.buyingPower()
            assertEquals("TTTC8908R", real.takeApi().getHeader("tr_id"))
        }
    }
}
