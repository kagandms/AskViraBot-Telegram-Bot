import logging

from config import supabase

logger = logging.getLogger(__name__)


# --- WEB GAMES (NEW) ---
def save_web_game_score(user_id: int | str, game_type: str, score: int, difficulty: str | None = None) -> bool:
    """Web oyunları için skor kaydeder."""
    if not supabase:
        return False
    try:
        # Önce RPC fonksiyonunu dene (daha güvenli ve atomic olabilir)
        try:
            supabase.rpc(
                "save_game_score",
                {"p_user_id": str(user_id), "p_game_type": game_type, "p_score": score, "p_difficulty": difficulty},
            ).execute()
            return True
        except Exception:
            # RPC yoksa veya hata verirse direkt tabloya yazmayı dene
            data = {"user_id": str(user_id), "game_type": game_type, "score": score, "difficulty": difficulty}
            supabase.table("game_scores").insert(data).execute()
            return True
    except Exception as e:
        logger.error(f"Score save error ({game_type} - {user_id}): {e}")
        return False


def get_web_game_high_score(user_id: int | str, game_type: str) -> int:
    """Kullanıcının belirli bir oyundaki en yüksek skorunu getirir."""
    if not supabase:
        return 0
    try:
        # RPC dene
        try:
            response = supabase.rpc("get_high_score", {"p_user_id": str(user_id), "p_game_type": game_type}).execute()
            if response.data is not None:
                return int(response.data)
        except Exception:
            pass

        # Fallback: Klasik sorgu
        response = (
            supabase.table("game_scores")
            .select("score")
            .eq("user_id", str(user_id))
            .eq("game_type", game_type)
            .order("score", desc=True)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return int(response.data[0]["score"])
        return 0
    except Exception as e:
        logger.error(f"Get high score error ({game_type} - {user_id}): {e}")
        return 0


def get_web_game_stats(user_id: int | str) -> dict:
    """Tüm web oyunları için özet istatistikleri getirir."""
    games = ["snake", "2048", "flappy", "runner", "sudoku", "xox"]
    stats = {}
    for game in games:
        stats[game] = get_web_game_high_score(user_id, game)
    return stats


# --- LEGACY GAMES LOGGING ---
def log_xox_game(user_id: int | str, winner: str, difficulty: str) -> None:
    if not supabase:
        return
    try:
        data = {"user_id": str(user_id), "winner": winner, "difficulty": difficulty}
        supabase.table("xox_logs").insert(data).execute()
    except Exception as e:
        logger.error(f"XOX log hatası (User: {user_id}): {e}")


def log_tkm_game(user_id: int | str, user_move: str, bot_move: str, result: str) -> None:
    if not supabase:
        return
    try:
        data = {"user_id": str(user_id), "user_move": user_move, "bot_move": bot_move, "result": result}
        supabase.table("tkm_logs").insert(data).execute()
    except Exception as e:
        logger.error(f"TKM log hatası (User: {user_id}): {e}")


def log_coinflip(user_id: int | str, result: str) -> None:
    if not supabase:
        return
    try:
        data = {"user_id": str(user_id), "result": result}
        supabase.table("coinflip_logs").insert(data).execute()
    except Exception as e:
        logger.error(f"Coinflip log hatası (User: {user_id}): {e}")


def log_dice_roll(user_id: int | str, result: int) -> None:
    if not supabase:
        return
    try:
        data = {"user_id": str(user_id), "result": str(result)}
        supabase.table("dice_logs").insert(data).execute()
    except Exception as e:
        logger.error(f"Dice log hatası (User: {user_id}): {e}")


# --- LEGACY STATS ---
def get_user_xox_stats(user_id: int | str) -> dict[str, int]:
    if not supabase:
        return {"wins": 0, "losses": 0, "draws": 0, "total": 0}
    try:
        response = supabase.table("xox_logs").select("winner").eq("user_id", str(user_id)).execute()
        data = response.data if response.data else []
        wins = sum(1 for r in data if r.get("winner") == "X")
        losses = sum(1 for r in data if r.get("winner") == "O")
        draws = sum(1 for r in data if r.get("winner") == "Draw")
        return {"wins": wins, "losses": losses, "draws": draws, "total": len(data)}
    except Exception as e:
        logger.error(f"XOX stats hatası (User: {user_id}): {e}")
        return {"wins": 0, "losses": 0, "draws": 0, "total": 0}


def get_user_tkm_stats(user_id: int | str) -> dict[str, int]:
    if not supabase:
        return {"wins": 0, "losses": 0, "draws": 0, "total": 0}
    try:
        response = supabase.table("tkm_logs").select("result").eq("user_id", str(user_id)).execute()
        data = response.data if response.data else []
        wins = sum(1 for r in data if r.get("result") == "win")
        losses = sum(1 for r in data if r.get("result") == "lose")
        draws = sum(1 for r in data if r.get("result") == "draw")
        return {"wins": wins, "losses": losses, "draws": draws, "total": len(data)}
    except Exception as e:
        logger.error(f"TKM stats hatası (User: {user_id}): {e}")
        return {"wins": 0, "losses": 0, "draws": 0, "total": 0}
