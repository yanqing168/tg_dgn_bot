from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

ALLOWED_TABLES: List[str] = [
    "audit_logs",
    "content_configs",
    "price_configs",
    "setting_configs",
]


def find_db(candidates):
    """
    在一组候选路径中找到第一个存在的 DB 文件。
    """
    for p in candidates:
        path = Path(p)
        if path.exists():
            return path
    return None


def main():
    print("=== merge_bot_db_into_tg_db.py ===")
    print("本脚本会把 bot_db 中的以下表合并到 tg_db：")
    print("  ", ", ".join(ALLOWED_TABLES))
    print("⚠️ 请确认已执行 scripts/backup_dbs.py 备份数据库后再继续。\n")

    # 1. 定位两个数据库文件
    bot_db_path = find_db(["data/bot_db.sqlite", "data/bot.db"])
    tg_db_path = find_db(["data/tg_db.sqlite", "data/tg_bot.db"])

    if bot_db_path is None:
        print("[ERROR] 未找到 bot_db.sqlite / bot.db，请检查 data/ 目录。")
        return

    if tg_db_path is None:
        print("[ERROR] 未找到 tg_db.sqlite / tg_bot.db，请检查 data/ 目录。")
        return

    print(f"[INFO] 使用 bot_db: {bot_db_path}")
    print(f"[INFO] 使用 tg_db : {tg_db_path}\n")

    # 2. 连接两个库
    bot_conn = sqlite3.connect(bot_db_path)
    tg_conn = sqlite3.connect(tg_db_path)

    # 行工厂：可以通过列名访问
    bot_conn.row_factory = sqlite3.Row
    tg_conn.row_factory = sqlite3.Row

    bot_cur = bot_conn.cursor()
    tg_cur = tg_conn.cursor()

    try:
        # 3. 遍历 ALLOWED_TABLES 进行迁移
        for table in ALLOWED_TABLES:
            print(f"\n=== 处理表: {table} ===")

            # 3.1 确认 bot_db 中存在该表
            bot_cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            row = bot_cur.fetchone()
            if row is None or row["sql"] is None:
                print(f"[WARN] bot_db 中不存在表 {table}，跳过。")
                continue

            create_sql = row["sql"]
            print(f"[INFO] bot_db.{table} 的建表语句:\n  {create_sql}")

            # 3.2 如果 tg_db 中没有这张表，则创建
            tg_cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            tg_row = tg_cur.fetchone()
            if tg_row is None:
                print(f"[CREATE] tg_db 中不存在表 {table}，正在创建...")
                tg_cur.execute(create_sql)
                tg_conn.commit()
                print(f"[CREATE] 已在 tg_db 中创建表 {table}")
            else:
                print(f"[SKIP] tg_db 已存在表 {table}，跳过创建。")

            # 3.3 从 bot_db 中读取数据
            bot_cur.execute(f"SELECT * FROM {table}")
            rows = bot_cur.fetchall()
            if not rows:
                print(f"[INFO] bot_db.{table} 中没有数据，跳过插入。")
                continue

            # 3.4 动态构造 INSERT OR IGNORE 语句
            col_names = [desc[0] for desc in bot_cur.description]
            cols_str = ", ".join(col_names)
            params_str = ", ".join([f":{c}" for c in col_names])
            insert_sql = f"INSERT OR IGNORE INTO {table} ({cols_str}) VALUES ({params_str})"

            print(f"[INFO] 准备插入 {len(rows)} 行到 tg_db.{table} ...")

            # 将 sqlite3.Row 转换为 dict 以便命名参数插入
            data_dicts = [dict(r) for r in rows]
            tg_cur.executemany(insert_sql, data_dicts)
            tg_conn.commit()

            print(f"[INSERT] 已尝试插入 {len(rows)} 行到 tg_db.{table}（使用 INSERT OR IGNORE）")

        print("\n=== 合并完成 ===")
        print("建议现在运行 scripts/inspect_db_schemas.py 再次检查两边表结构与行数。")

    finally:
        bot_cur.close()
        tg_cur.close()
        bot_conn.close()
        tg_conn.close()


if __name__ == '__main__':
    main()


if __name__ == "__main__":
    main()
