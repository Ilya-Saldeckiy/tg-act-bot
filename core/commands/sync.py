#!/usr/bin/env python3

import subprocess
import sys

BLUE = "\033[94m"
RED = "\033[91m"
CYAN = "\033[96m"
GREEN = "\033[92m"
END = "\033[0m"


def exec_command(command: str) -> tuple[bool, str]:
    """Выполняет shell-команду и возвращает успех и результат."""
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        return True, result
    except subprocess.CalledProcessError as e:
        return False, e.output


def main():
    print(f"{CYAN}Синхронизация media...{END}")
    success, result = exec_command(
        "rsync -cvzr --progress root@176.124.218.100:../home/tg-bot/tg-act-bot/acts/ ./acts/"
    )
    if not success:
        print(f"{RED}{result}{END}")
        sys.exit(1)

    success, result = exec_command(
        "rsync -cvzr --progress root@176.124.218.100:../home/tg-bot/tg-act-bot/photos/ ./photos/"
    )
    if not success:
        print(f"{RED}{result}{END}")
        sys.exit(1)

    print(f"{CYAN}!!! Синхронизация БД !!!{END}")

    dump_path = "./"
    success, result = exec_command(
        f"rsync -vz --progress -e ssh root@176.124.218.100:../home/tg-bot/tg-act-bot/db.sqlite3.db {dump_path}"
    )
    if not success:
        print(f"{RED}{result}{END}")
        sys.exit(1)

    print(f"{CYAN}!!! Выполняю миграции !!!{END}")
    
    success, result = exec_command("alembic upgrade head")
    
    if not success:
        print(f"{RED}{result}{END}")
        sys.exit(1)

    print(f"{GREEN}!!! Синхронизация завершена !!!{END}")


if __name__ == "__main__":
    main()
