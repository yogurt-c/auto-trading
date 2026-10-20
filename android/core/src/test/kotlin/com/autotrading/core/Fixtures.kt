package com.autotrading.core

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File

/** shared/fixtures 읽기 — research(Python)가 생성한 입력 → 기대 출력. */
object Fixtures {
    private val root = File(requireNotNull(System.getProperty("fixtures.dir")) { "fixtures.dir 미설정" })

    fun load(category: String): Map<String, JsonObject> =
        root.resolve(category).listFiles { f -> f.extension == "json" }!!
            .sortedBy { it.name }
            .associate { it.nameWithoutExtension to Json.parseToJsonElement(it.readText()).jsonObject }
}

fun JsonElement.doubles(): Map<String, Double> = jsonObject.mapValues { it.value.jsonPrimitive.double }

fun JsonElement.ints(): Map<String, Int> = jsonObject.mapValues { it.value.jsonPrimitive.int }

fun JsonElement.orders(side: Side): List<OrderIntent> = jsonArray.map {
    OrderIntent(it.jsonObject["code"]!!.jsonPrimitive.content, side, it.jsonObject["qty"]!!.jsonPrimitive.int)
}
