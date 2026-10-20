package com.autotrading.core

import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.junit.jupiter.api.assertThrows

class RebalancePlannerTest {
    @TestFactory
    fun `shared fixtures와 같은 주문을 낸다`(): List<DynamicTest> =
        Fixtures.load("rebalance").map { (name, fixture) ->
            DynamicTest.dynamicTest(name) {
                val input = fixture["input"]!!.jsonObject
                val expected = fixture["expected"]!!.jsonObject
                val params = input["params"]!!.doubles()
                val planner = RebalancePlanner(
                    cashBuffer = params.getValue("cash_buffer"),
                    minOrderFraction = params.getValue("min_order_fraction"),
                    costReserve = params.getValue("cost_reserve"),
                    managedCodes = input["managed_codes"]!!.jsonArray.map { it.jsonPrimitive.content }.toSet(),
                )
                val prices = input["prices"]!!.doubles()
                val plan = planner.plan(
                    weights = input["weights"]!!.doubles(),
                    holdings = input["holdings"]!!.ints(),
                    prices = prices,
                    cash = input["cash"]!!.jsonPrimitive.double,
                )
                assertEquals(expected["equity"]!!.jsonPrimitive.double, plan.equity, 1e-6)
                assertEquals(expected["targets"]!!.ints(), plan.targets)
                assertEquals(expected["sells"]!!.orders(Side.SELL), plan.sells)

                val buys = planner.planBuys(
                    holdings = expected["holdings_after_sells"]!!.ints(),
                    targets = plan.targets,
                    prices = prices,
                    cash = expected["cash_after_sells"]!!.jsonPrimitive.double,
                    equity = plan.equity,
                )
                assertEquals(expected["buys"]!!.orders(Side.BUY), buys)
            }
        }

    @Test
    fun `관리 대상이 아닌 종목 비중은 거부한다`() {
        assertThrows<IllegalArgumentException> {
            RebalancePlanner().plan(mapOf("005930" to 1.0), emptyMap(), mapOf("005930" to 70_000.0), 1e6)
        }
    }

    @Test
    fun `가격이 없거나 0이면 거부한다`() {
        val weights = Profile.STABLE.weightsByCode
        assertThrows<IllegalArgumentException> {
            RebalancePlanner().plan(weights, emptyMap(), mapOf("069500" to 35_000.0), 1e6)
        }
        assertThrows<IllegalArgumentException> {
            RebalancePlanner().plan(weights, emptyMap(), mapOf("069500" to 35_000.0, "360750" to 0.0), 1e6)
        }
    }
}
