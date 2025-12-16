"""
Deepgram Service
Handles audio transcription using Deepgram Nova-2
"""
from deepgram import DeepgramClient, PrerecordedOptions
from typing import Dict, Any, Optional
import io


class DeepgramService:
    """Service for Deepgram audio transcription."""
    
    def __init__(self, api_key: str):
        self.client = DeepgramClient(api_key)
        self.default_options = PrerecordedOptions(
            model="nova-2",
            language="en",
            smart_format=True,
            punctuate=True,
            diarize=True,
            paragraphs=True,
        )
    
    def transcribe_file(
        self, 
        file_content: bytes,
        options: Optional[PrerecordedOptions] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file content.
        
        Args:
            file_content: Raw bytes of the audio file
            options: Optional custom transcription options
            
        Returns:
            Dict with text, confidence, duration, and any errors
        """
        try:
            payload = {"buffer": file_content}
            opts = options or self.default_options
            
            response = self.client.listen.rest.v("1").transcribe_file(payload, opts)
            result = response.to_dict()
            
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            confidence = result["results"]["channels"][0]["alternatives"][0].get("confidence", 0)
            duration = result.get("metadata", {}).get("duration", 0)
            
            return {
                "text": transcript,
                "confidence": confidence,
                "duration": duration,
                "success": True
            }
            
        except Exception as e:
            return {
                "text": "",
                "confidence": 0,
                "duration": 0,
                "success": False,
                "error": str(e)
            }
    
    def transcribe_url(
        self, 
        url: str,
        options: Optional[PrerecordedOptions] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from URL.
        
        Args:
            url: URL of the audio file
            options: Optional custom transcription options
            
        Returns:
            Dict with text, confidence, duration, and any errors
        """
        try:
            opts = options or self.default_options
            
            response = self.client.listen.rest.v("1").transcribe_url(
                {"url": url}, opts
            )
            result = response.to_dict()
            
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            confidence = result["results"]["channels"][0]["alternatives"][0].get("confidence", 0)
            duration = result.get("metadata", {}).get("duration", 0)
            
            return {
                "text": transcript,
                "confidence": confidence,
                "duration": duration,
                "success": True
            }
            
        except Exception as e:
            return {
                "text": "",
                "confidence": 0,
                "duration": 0,
                "success": False,
                "error": str(e)
            }
