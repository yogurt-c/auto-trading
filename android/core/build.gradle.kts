// 순수 Kotlin (Android 의존 없음) — 리밸런싱 계산·거래일 달력
plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
}

// Android 모듈과 맞추기 위해 Java 17 바이트코드로 컴파일 (빌드 JDK는 17 이상 아무거나)
java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    implementation(libs.kotlinx.serialization.json)
    testImplementation(platform(libs.junit.bom))
    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.launcher)
}

tasks.test {
    useJUnitPlatform()
    // shared/fixtures — research(Python)가 생성한 기대값을 Kotlin 구현과 대조
    systemProperty("fixtures.dir", rootDir.resolve("../shared/fixtures").absolutePath)
}
