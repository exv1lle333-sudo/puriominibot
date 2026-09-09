from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
UPDATER = ROOT / "update_purio_ui.py"

OLD = '''    js = replace_once(
        js,
        "  await resumeCrashRound();",
        "  if (resume) await resumeCrashRound();",
        "Возобновление Crash",
    )'''

NEW = r'''    js = replace_once(
        js,
        "  renderPaytable();\n  await resumeCrashRound();",
        "  renderPaytable();\n  if (resume) await resumeCrashRound();",
        "Возобновление Crash",
    )'''


def main():
    if not UPDATER.is_file():
        print(
            "Не найден update_purio_ui.py.\n"
            "Положи этот файл рядом с ним, в корень проекта."
        )
        return 1

    source = UPDATER.read_text(encoding="utf-8-sig")

    if source.count(OLD) == 1:
        fixed = source.replace(OLD, NEW, 1)

        # Проверяем синтаксис до записи.
        compile(fixed, str(UPDATER), "exec")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = ROOT / f"update_purio_ui.py.backup-{stamp}"
        shutil.copy2(UPDATER, backup)

        try:
            UPDATER.write_text(fixed, encoding="utf-8")
        except Exception:
            shutil.copy2(backup, UPDATER)
            raise

        print("Ошибка поиска вызова Crash исправлена.")
        print(f"Копия старого скрипта: {backup.name}")

    elif source.count(NEW) == 1:
        print("Исправление уже установлено.")
    else:
        print(
            "Не удалось найти ожидаемый блок в update_purio_ui.py.\n"
            "Ничего не изменено. Пришли содержимое пункта # 12 "
            "из этого файла."
        )
        return 1

    print("\nЗапускаем обновление интерфейса...\n", flush=True)

    result = subprocess.run(
        [sys.executable, str(UPDATER)],
        cwd=str(ROOT),
        check=False,
    )

    if result.returncode != 0:
        print(
            "\nОбновление остановилось с ошибкой. "
            "Пришли текст ошибки из окна выше."
        )

    return result.returncode


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        print(f"\nОшибка: {exc}")
        exit_code = 1

    sys.exit(exit_code)