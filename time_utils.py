"""
時刻関連ユーティリティ
全ての時刻表示を日本時間（JST）に統一
"""
from datetime import datetime, timezone, timedelta


def now_jst() -> datetime:
    """現在の日本時間（JST: UTC+9）を取得"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst)


def to_jst_str(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """datetimeオブジェクトを日本時間文字列に変換"""
    if dt.tzinfo is None:
        # timezone-naiveの場合、UTCとして扱う
        dt = dt.replace(tzinfo=timezone.utc)
    
    # UTCからJSTに変換
    jst = timezone(timedelta(hours=9))
    dt_jst = dt.astimezone(jst)
    
    return dt_jst.strftime(format_str)


def isoformat_jst(dt: datetime = None) -> str:
    """ISOフォーマットで日本時間の文字列を取得"""
    if dt is None:
        dt = now_jst()
    elif dt.tzinfo is None:
        # timezone-naiveの場合、JSTとして扱う
        jst = timezone(timedelta(hours=9))
        dt = dt.replace(tzinfo=jst)
    else:
        # JSTに変換
        jst = timezone(timedelta(hours=9))
        dt = dt.astimezone(jst)
    
    return dt.isoformat()

