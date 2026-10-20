package com.autotrading.core

import kotlinx.serialization.json.jsonObject
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class ProfileTest {
    @Test
    fun `성향 비중이 백테스트 사전 등록과 같다`() {
        val expected = Fixtures.load("profiles").getValue("app_profiles")["expected"]!!.jsonObject
        assertEquals(expected["stable"]!!.doubles(), Profile.STABLE.weightsByCode)
        assertEquals(expected["conservative"]!!.doubles(), Profile.CONSERVATIVE.weightsByCode)
    }

    @Test
    fun `성향 비중 합은 1`() {
        Profile.entries.forEach { assertEquals(1.0, it.weights.values.sum(), 1e-12, it.name) }
    }
}
