from groq import Groq
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

class ContractSummarizer:
    """Service for summarizing contracts using Groq's OpenAI GPT-OSS-20B model."""
    
    def __init__(self):
        try:
            print(f"🔧 Initializing Groq client...")
            print(f"🔑 API Key configured: {'Yes' if settings.groq_api_key and len(settings.groq_api_key) > 10 else 'No'}")
            print(f"🤖 Model: {settings.groq_model}")
            
            if not settings.groq_api_key:
                raise Exception("Groq API key not configured. Please set GROQ_API_KEY in your .env file")
            
            self.client = Groq(api_key=settings.groq_api_key)
            self.model = settings.groq_model
            self.executor = ThreadPoolExecutor(max_workers=2)
            print(f"✅ Groq client initialized successfully with model: {self.model}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Groq client: {str(e)}")
            raise
    
    async def summarize(self, text: str, max_length: int = 300, min_length: int = 50) -> str:
        """Summarize the input text using Groq API."""
        try:
            if not text or len(text.strip()) < 50:
                return "Text is too short to summarize effectively."
            
            # Handle very long documents by chunking
            if len(text) > 8000:  # Groq has token limits
                chunks = self._chunk_text(text, max_chunk_size=6000)
                summaries = []
                
                for chunk in chunks:
                    if len(chunk.strip()) < 100:  # Skip very short chunks
                        continue
                    
                    chunk_summary = await self._summarize_chunk(chunk, max_length // len(chunks))
                    if chunk_summary:
                        summaries.append(chunk_summary)
                
                if len(summaries) == 0:
                    return "Unable to generate summary - text may be too short or invalid."
                elif len(summaries) == 1:
                    return summaries[0]
                else:
                    # Combine and re-summarize if multiple chunks
                    combined = " ".join(summaries)
                    return await self._summarize_chunk(combined, max_length)
            else:
                # Single chunk processing
                return await self._summarize_chunk(text, max_length)
                
        except Exception as e:
            print(f"Error in summarization: {str(e)}")
            return self._simple_summary(text, max_length)
    
    async def _summarize_chunk(self, text: str, max_length: int = 300) -> str:
        """Summarize a single chunk of text using Groq."""
        try:
            # Validate input
            if not text or len(text.strip()) < 10:
                print("❌ Text chunk is too short for summarization")
                return ""
            
            # Detect language and create appropriate prompt
            language_instruction = self._detect_language_instruction(text)
            
            prompt = f"""Please provide a concise and comprehensive summary of the following document. 
The summary should capture the key points, main ideas, and important details while being approximately {max_length} words or less.
{language_instruction}

Document:
{text}

Summary:"""

            print(f"🔄 Sending request to Groq API with model: {self.model}")
            print(f"📝 Text length: {len(text)} characters")
            
            # Use thread executor to make the blocking call async
            completion = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=min(max_length * 3, 2048),  # Use max_tokens instead of max_completion_tokens
                    top_p=1,
                    stream=False,
                    stop=None
                )
            )
            
            print(f"✅ Received response from Groq API")
            
            if completion and hasattr(completion, 'choices') and completion.choices and len(completion.choices) > 0:
                if hasattr(completion.choices[0], 'message') and hasattr(completion.choices[0].message, 'content'):
                    summary = completion.choices[0].message.content
                    if summary:
                        summary = summary.strip()
                        print(f"✅ Summary generated: {len(summary)} characters")
                        return summary
                    else:
                        print("❌ Summary content is empty")
                        return ""
                else:
                    print("❌ Invalid response structure from Groq API")
                    return ""
            else:
                print("❌ No choices returned from Groq API")
                return ""
                
        except Exception as e:
            print(f"❌ Error in Groq API call: {str(e)}")
            print(f"❌ Error type: {type(e).__name__}")
            return ""
    
    def _detect_language_instruction(self, text: str) -> str:
        """Detect the language of the text and provide appropriate instruction."""
        # Common Vietnamese words and patterns
        vietnamese_indicators = [
            'và', 'của', 'là', 'có', 'được', 'cho', 'từ', 'trong', 'với', 'các', 
            'này', 'đó', 'để', 'những', 'một', 'về', 'theo', 'như', 'đã', 'sẽ',
            'tại', 'do', 'khi', 'mà', 'nếu', 'hoặc', 'nhưng', 'vì', 'bởi', 'thì',
            'ở', 'trên', 'dưới', 'giữa', 'sau', 'trước', 'ngoài', 'trong'
        ]
        
        # Common English words
        english_indicators = [
            'the', 'and', 'of', 'to', 'in', 'for', 'with', 'on', 'at', 'by',
            'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may'
        ]
        
        # Convert to lowercase for comparison
        text_lower = text.lower()
        
        # Count Vietnamese indicators
        vietnamese_count = sum(1 for word in vietnamese_indicators if f' {word} ' in text_lower or text_lower.startswith(f'{word} ') or text_lower.endswith(f' {word}'))
        
        # Count English indicators
        english_count = sum(1 for word in english_indicators if f' {word} ' in text_lower or text_lower.startswith(f'{word} ') or text_lower.endswith(f' {word}'))
        
        # Check for Vietnamese specific characters
        vietnamese_chars = ['ă', 'â', 'đ', 'ê', 'ô', 'ơ', 'ư', 'á', 'à', 'ả', 'ã', 'ạ', 'é', 'è', 'ẻ', 'ẽ', 'ẹ', 'í', 'ì', 'ỉ', 'ĩ', 'ị', 'ó', 'ò', 'ỏ', 'õ', 'ọ', 'ú', 'ù', 'ủ', 'ũ', 'ụ', 'ý', 'ỳ', 'ỷ', 'ỹ', 'ỵ']
        has_vietnamese_chars = any(char in text_lower for char in vietnamese_chars)
        
        print(f"🔍 Language detection - Vietnamese words: {vietnamese_count}, English words: {english_count}, Vietnamese chars: {has_vietnamese_chars}")
        
        # Determine language based on indicators
        if vietnamese_count > english_count or has_vietnamese_chars:
            return "IMPORTANT: Please write the summary in Vietnamese language (tiếng Việt). The document is in Vietnamese, so the summary must also be in Vietnamese."
        else:
            return "Please write the summary in English."

    def _chunk_text(self, text: str, max_chunk_size: int = 6000) -> list:
        """Split text into chunks suitable for the model."""
        # Split by paragraphs first for better context preservation
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size, start new chunk
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If no chunks created (very long single paragraph), split by sentences
        if not chunks and text:
            sentences = text.split('. ')
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
                else:
                    current_chunk += sentence + ". "
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        
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
        """Extract key points from the text using Groq."""
        try:
            # Detect language and create appropriate prompt
            language_instruction = self._detect_language_instruction(text)
            
            prompt = f"""Please extract the 5 most important key points from the following document. 
Return them as a numbered list, with each point being a concise but complete statement.
{language_instruction}

Document:
{text}

Key Points:"""

            completion = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.5,
                    max_tokens=1024,  # Use max_tokens instead of max_completion_tokens
                    top_p=1,
                    stream=False,
                    stop=None
                )
            )
            
            if completion.choices and len(completion.choices) > 0:
                key_points_text = completion.choices[0].message.content.strip()
                # Parse the numbered list into individual points
                lines = key_points_text.split('\n')
                key_points = []
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Remove numbering and clean up
                        cleaned = line.lstrip('0123456789.-• ').strip()
                        if cleaned:
                            key_points.append(cleaned)
                
                return key_points[:5] if key_points else ["Unable to extract key points from this document."]
            else:
                return ["Unable to extract key points from this document."]
                
        except Exception as e:
            print(f"Error extracting key points: {str(e)}")
            return ["Unable to extract key points from this document."]
    
    def close(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)