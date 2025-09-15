from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from app.core.config import settings

class ContractSummarizer:
    """Service for summarizing contracts using Hugging Face models."""
    
    def __init__(self):
        self.model_name = settings.hf_model_summarization
        self.summarizer = None
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the summarization model and tokenizer."""
        try:
            # Load tokenizer and model separately for better control
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            # Create pipeline
            self.summarizer = pipeline(
                "summarization",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1  # Use GPU if available
            )
            print(f"✅ Summarization model loaded: {self.model_name}")
            
        except Exception as e:
            print(f"❌ Error loading summarization model: {str(e)}")
            # Fallback to a simpler model if BART fails
            try:
                self.model_name = "sshleifer/distilbart-cnn-12-6"
                self.summarizer = pipeline("summarization", model=self.model_name)
                print(f"✅ Fallback summarization model loaded: {self.model_name}")
            except Exception as fallback_error:
                print(f"❌ Fallback model also failed: {str(fallback_error)}")
                raise Exception("Failed to load any summarization model")
    
    async def summarize(self, text: str, max_length: int = 300, min_length: int = 50) -> str:
        """Summarize the input text."""
        try:
            if not self.summarizer:
                raise Exception("Summarization model not loaded")
            
            # Handle very long documents by chunking
            chunks = self._chunk_text(text, max_chunk_size=1000)
            summaries = []
            
            for chunk in chunks:
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                
                # Generate summary for each chunk
                result = self.summarizer(
                    chunk,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False,
                    truncation=True
                )
                
                if result and len(result) > 0:
                    summaries.append(result[0]['summary_text'])
            
            # Combine summaries from all chunks
            if len(summaries) == 0:
                return "Unable to generate summary - text may be too short or invalid."
            elif len(summaries) == 1:
                return summaries[0]
            else:
                # If multiple chunks, summarize the combined summaries
                combined_summary = " ".join(summaries)
                if len(combined_summary) > 1000:
                    # Re-summarize if combined summary is too long
                    final_result = self.summarizer(
                        combined_summary,
                        max_length=max_length,
                        min_length=min_length,
                        do_sample=False,
                        truncation=True
                    )
                    return final_result[0]['summary_text']
                else:
                    return combined_summary
                    
        except Exception as e:
            print(f"Error in summarization: {str(e)}")
            # Fallback to simple text truncation
            return self._simple_summary(text, max_length)
    
    def _chunk_text(self, text: str, max_chunk_size: int = 1000) -> list:
        """Split text into chunks suitable for the model."""
        # Split by sentences first
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, start new chunk
            if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                current_chunk += sentence + ". "
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If no chunks created (very long single sentence), split by words
        if not chunks and text:
            words = text.split()
            for i in range(0, len(words), max_chunk_size // 10):  # Roughly 10 chars per word
                chunk_words = words[i:i + max_chunk_size // 10]
                chunks.append(" ".join(chunk_words))
        
        return chunks
    
    def _simple_summary(self, text: str, max_length: int = 300) -> str:
        """Simple fallback summarization by taking first paragraphs."""
        paragraphs = text.split('\n\n')
        summary = ""
        
        for paragraph in paragraphs:
            if len(summary) + len(paragraph) < max_length:
                summary += paragraph + " "
            else:
                break
        
        if not summary.strip():
            # If no paragraphs, take first sentences
            sentences = text.split('. ')
            for sentence in sentences[:3]:  # Take first 3 sentences
                summary += sentence + ". "
        
        return summary.strip() or "Unable to generate summary from this document."
    
    async def get_key_points(self, text: str) -> list:
        """Extract key points from the text (simplified implementation)."""
        try:
            # Use the summarizer to get a longer summary first
            detailed_summary = await self.summarize(text, max_length=500, min_length=100)
            
            # Split into key points (simple sentence-based approach)
            sentences = detailed_summary.split('. ')
            key_points = [sentence.strip() + '.' for sentence in sentences if len(sentence.strip()) > 20]
            
            return key_points[:5]  # Return top 5 key points
            
        except Exception as e:
            print(f"Error extracting key points: {str(e)}")
            return ["Unable to extract key points from this document."]