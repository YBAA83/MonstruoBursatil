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

    def analyze_asset(self, symbol, price_data, context="Neutral", image_bytes=None):
        """
        Analyzes an asset using Gemini based on price action, news sentiment, and optional chart image.
        Returns a structured response: Signal (Green/Yellow/Red), Reasoning, and Key Levels.
        """
        if not self.client:
            return {
                "signal": "Gray",
                "reasoning": "AI Model not initialized. Check API Key.",
                "levels": "N/A"
            }

        # Construct Prompt
        vision_instruction = "IMPORTANT: An image of the chart is provided. Use it to identify visual patterns (triangles, channels, support zones) and combine it with the numerical data." if image_bytes else ""
        
        prompt = f"""
        You are a seasoned financial analyst for the "Monstruo Bursátil" ecosystem. 
        Your task is to analyze the following asset based on provided data and optional visual chart.

        Asset: {symbol}
        Analysis Data Context (MTF Trends, Indicators, Sentiment, Walls):
        {context}

        Recent Price Data (OHLCV last candles):
        {price_data.tail(10).to_string()}

        {vision_instruction}

        Instructions:
        1. Evaluate Multi-Temporal Trends (MTF) and Technical Indicators (RSI, MACD, BB).
        2. Whale Activity & Order Book: Incorporate volume spikes and walls.
        3. Visual Patterns: If an image is provided, describe the structure you see.
        4. Final Judgment: Combine visual and technical data for the signal.

        Output Style:
        Signal: [GREEN/YELLOW/RED]
        Reasoning: [TEXT - Concise max 3 sentences. Mention specific patterns or data points used.]
        Levels: [TEXT - Define support and resistance]
        """
        
        try:
            contents = [prompt]
            if image_bytes:
                # The google-genai SDK 1.0+ handles bytes directly in contents list if wrapped or as a Part
                from google.genai import types
                contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=contents
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
