import requests
import json
import time
from datetime import datetime, timezone

WEBHOOK_URL = "https://discord.com/api/webhooks/1425456204498472960/ashuNlX0ZIKO1Uzw7VVM6PLG1sqzd57LEGuEnJKSBdQwh2h9Y2oyMv7MdTgkLAjAHARQ"
CHECK_INTERVAL = 60  # 秒

def fetch_worldstate():
    """Warframe公式APIからworldStateデータを取得"""
    url = "https://content.warframe.com/dynamic/worldState.php"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] fetch_worldstate: {e}")
        return {}

def notify_discord(msg):
    """Discordへ通知"""
    try:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"[ERROR] notify_discord: {e}")

def relic_tier(modifier):
    """VoidT1などの内部名をレリック名に変換"""
    mapping = {
        "VoidT1": "Lith",
        "VoidT2": "Meso",
        "VoidT3": "Neo",
        "VoidT4": "Axi",
        "VoidT5": "Requiem",
        "VoidT6": "Omnia",
    }
    return mapping.get(modifier, modifier)

def extract_expiry_seconds(expiry_dict):
    """多重辞書対応のExpiry抽出"""
    try:
        millis = int(
            expiry_dict.get("$date", {}).get("$numberLong") or
            expiry_dict.get("$date") or
            expiry_dict.get("$numberLong") or
            0
        )
        return millis / 1000
    except Exception:
        return 0

def main():
    print("監視開始...（worldState直参照／Steel優先／Extermination・Void Cascade限定／Kuva・VoidStorm除外／Tier名変換対応）")
    notified = set()

    while True:
        try:
            ws = fetch_worldstate()
            if not ws:
                time.sleep(60)
                continue

            fissures = ws.get("ActiveMissions", [])
            now = datetime.now(timezone.utc).timestamp()

            # Steel存在チェック
            has_steel = any(
                f.get("Hard", False)
                and f.get("MissionType") in ["MT_EXTERMINATION", "MT_VOID_CASCADE"]
                for f in fissures
            )

            for fiss in fissures:
                node = fiss.get("Node", "")
                mission_type = fiss.get("MissionType", "")
                hard = fiss.get("Hard", False)

                # Steel優先：Steelがある場合は通常を無視
                if has_steel and not hard:
                    continue

                # 除外条件
                if "Kuva Fortress" in node:
                    continue
                if "Skirmish" in mission_type or fiss.get("ActiveMissionTier", "") == "VoidStorm":
                    continue

                # 対象ミッション（公式内部定数対応）
                if mission_type not in ["MT_EXTERMINATION", "MT_VOID_CASCADE"]:
                    continue

                fid = fiss.get("_id", {}).get("$oid", "")
                if fid in notified:
                    continue

                expiry_ts = extract_expiry_seconds(fiss.get("Expiry", {}))
                if expiry_ts == 0:
                    continue

                modifier = fiss.get("Modifier", "")
                tier = relic_tier(modifier)
                kind = "Steel Path" if hard else "Normal"
                msg = f"{kind} Fissure: {node} ({mission_type}) [{tier}]"

                print(f"[{datetime.now()}] Notified: {msg}")
                notify_discord(msg)
                notified.add(fid)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"[ERROR] loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()