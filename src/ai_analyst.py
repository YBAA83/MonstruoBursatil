from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

class AIAnalyst:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables. Functionality limited.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def analyze_asset(self, symbol, price_data, news_sentiment="Neutral"):
        """
        Analyzes an asset using Gemini based on price action and news sentiment.
        Returns a structured response: Signal (Green/Yellow/Red), Reasoning, and Key Levels.
        """
        if not self.client:
            return {
                "signal": "Gray",
                "reasoning": "AI Model not initialized. Check API Key.",
                "levels": "N/A"
            }

        # Construct Prompt
        prompt = f"""
        You are a seasoned financial analyst for the "Monstruo Bursátil" ecosystem. 
        Your task is to analyze the following cryptocurrency asset based on provided data keys.

        Asset: {symbol}
        Analysis Data Context (MTF Trends, Indicators, Sentiment):
        {news_sentiment}

        Recent Price Data (OHLCV last 5 hours of primary timeframe):
        {price_data.tail().to_string()}

        Instructions:
        1. Evaluate Multi-Temporal Trends (MTF): If 15m is bullish but 4h is bearish, the signal should be YELLOW (Sideways).
        2. Technical Indicators: Use RSI, MACD, and Bollinger Bands to refine the signal.
        3. Whale Activity: If a volume spike is mentioned, prioritize a GREEN or RED signal depending on price direction.
        4. Sentiment: Incorporate headlines into the reasoning.

        Output Style:
        Signal: [GREEN/YELLOW/RED]
        Reasoning: [TEXT - Concise max 2 sentences. Reference indicators if they justify the signal.]
        Levels: [TEXT - Define support and resistance]
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )
            parsed = self._parse_response(response.text)
            
            # Add token usage metadata
            usage = response.usage_metadata
            parsed["usage"] = {
                "prompt_tokens": usage.prompt_token_count,
                "candidates_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count
            }
            return parsed
        except Exception as e:
            error_msg = str(e)
            print(f"Error analyzing asset {symbol}: {error_msg}")
            # Identify specific errors for the user
            reason = "Error en generación IA."
            if "quota" in error_msg.lower():
                reason = "Límite de cuota API excedido."
            elif "api key" in error_msg.lower():
                reason = "Error de API Key. Revisa .env"
                
            return {
                "signal": "Gray",
                "reasoning": f"{reason} ({error_msg[:50]}...)",
                "levels": "N/A"
            }

    def _parse_response(self, text):
        """Simple parser to extract signal and reasoning/levels from AI response."""
        lines = text.strip().split('\n')
        result = {"signal": "Yellow", "reasoning": "Análisis pendiente", "levels": "N/A"}
        
        for line in lines:
            if "Signal:" in line:
                if "GREEN" in line.upper():
                    result["signal"] = "Green"
                elif "RED" in line.upper():
                    result["signal"] = "Red"
                else:
                    result["signal"] = "Yellow"
            elif "Reasoning:" in line:
                result["reasoning"] = line.replace("Reasoning:", "").strip()
            elif "Levels:" in line:
                result["levels"] = line.replace("Levels:", "").strip()
        
        return result

if __name__ == "__main__":
    # Test execution (mock data)
    import pandas as pd
    mock_data = pd.DataFrame({
        'open': [100, 101, 102, 101, 103],
        'close': [101, 102, 101, 103, 104],
        'volume': [500, 600, 550, 700, 800]
    })
    analyst = AIAnalyst()
    print(analyst.analyze_asset("BTCUSDT", mock_data))
