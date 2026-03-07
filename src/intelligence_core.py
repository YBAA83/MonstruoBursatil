import logging
from datetime import datetime

class IntelligenceCore:
    """Analyzes past performance to generate adaptive trading rules."""
    def __init__(self, journal):
        self.journal = journal
        self.logger = logging.getLogger("IntelligenceCore")
        self.learned_lessons = []

    def reflect_on_performance(self):
        """Analyzes recent trades and extracts 'lessons learned'."""
        recent_trades = self.journal.get_recent_trades(limit=10)
        if not recent_trades:
            return "Aún no hay suficientes datos para aprender. Mantener estrategia conservadora."

        wins = [t for t in recent_trades if t['pnl_pct'] > 0]
        losses = [t for t in recent_trades if t['pnl_pct'] <= 0]
        
        lessons = []
        
        # Simple heuristic-based learning
        if len(losses) >= 3:
            lessons.append("🚨 ALERTA: Hemos tenido 3 o más pérdidas recientes. Ser EXTREMADAMENTE selectivo con las señales 'Green'.")
        
        if wins:
            avg_win = sum([t['pnl_pct'] for t in wins]) / len(wins)
            if avg_win > 2.0:
                 lessons.append(f"✅ ÉXITO: Las últimas ganancias promedian {avg_win:.1f}%. La estrategia de tendencia está funcionando.")

        for trade in losses:
            if "RSI" in trade.get('reason', '') and "overbought" in trade.get('reason', ''):
                lessons.append(f"⚠️ LECCIÓN: Evitar entrar en LONG cuando el RSI indica sobrecompra extrema, incluso con señal Green.")

        self.learned_lessons = lessons
        return "\n".join(lessons) if lessons else "La estrategia actual es sólida. Seguir operando con normalidad."

    def get_context_for_ai(self):
        """Returns the learning block for the AI prompt."""
        reflection = self.reflect_on_performance()
        return f"\n### 🧠 MEMORIA DE CORTO PLAZO (AUTO-CORRECCIÓN):\n{reflection}\n"
