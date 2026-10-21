package com.autotrading.engine

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.time.YearMonth

/**
 * 달마다 `run-YYYY-MM.json` 파일 1개. 임시 파일에 쓰고 fsync한 뒤 이름을 바꿔(원자적 교체)
 * 쓰는 도중 앱이 죽어도 이전 내용이나 새 내용 중 하나만 남는다.
 */
class FileRunStore(private val dir: File) : RunStore {
    init {
        require(dir.isDirectory || dir.mkdirs()) { "저장 폴더를 만들 수 없습니다: $dir" }
    }

    @Synchronized
    override fun load(month: YearMonth): MonthlyRun? =
        fileOf(month).takeIf(File::exists)?.readText()?.let(MonthlyRun::fromJson)

    @Synchronized
    override fun save(run: MonthlyRun) {
        val target = fileOf(run.month)
        val tmp = File(dir, "${target.name}.tmp")
        FileOutputStream(tmp).use { out ->
            out.write(run.toJson().toByteArray())
            out.fd.sync()
        }
        Files.move(tmp.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }

    /** 기록 화면용 (최근 달부터). 읽을 수 없는 파일 하나 때문에 화면이 죽지 않도록 따로 모은다. */
    data class History(val runs: List<MonthlyRun>, val unreadable: List<String>)

    @Synchronized
    fun history(): History {
        val files = dir.listFiles { f -> PATTERN.matches(f.name) }.orEmpty().sortedByDescending { it.name }
        val read = files.map { it.name to runCatching { MonthlyRun.fromJson(it.readText()) }.getOrNull() }
        return History(read.mapNotNull { it.second }, read.filter { it.second == null }.map { it.first })
    }

    private fun fileOf(month: YearMonth) = File(dir, "run-$month.json")

    private companion object {
        val PATTERN = Regex("""run-\d{4}-\d{2}\.json""")
    }
}
