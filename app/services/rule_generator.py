import openai
import google.generativeai as genai
import json
from typing import Dict, List, Any
from app.core.config import settings

class RuleGenerator:
    """Service for generating business rules from contracts using AI APIs."""
    
    def __init__(self):
        self.openai_client = None
        self.google_model = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI API clients."""
        # Initialize OpenAI
        if settings.openai_api_key:
            try:
                openai.api_key = settings.openai_api_key
                self.openai_client = openai
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"❌ Error initializing OpenAI: {str(e)}")
        
        # Initialize Google Generative AI
        if settings.google_api_key:
            try:
                genai.configure(api_key=settings.google_api_key)
                self.google_model = genai.GenerativeModel(settings.google_model)
                print("✅ Google AI client initialized")
            except Exception as e:
                print(f"❌ Error initializing Google AI: {str(e)}")
    
    async def generate_rules(self, text: str, document_type: str = "contract", provider: str = "openai") -> Dict[str, Any]:
        """Generate business rules from document text."""
        try:
            if provider == "openai" and self.openai_client:
                return await self._generate_rules_openai(text, document_type)
            elif provider == "google" and self.google_model:
                return await self._generate_rules_google(text, document_type)
            else:
                # Fallback to simple pattern-based rule extraction
                return await self._generate_rules_fallback(text, document_type)
                
        except Exception as e:
            print(f"Error generating rules: {str(e)}")
            return await self._generate_rules_fallback(text, document_type)
    
    async def _generate_rules_openai(self, text: str, document_type: str) -> Dict[str, Any]:
        """Generate rules using OpenAI GPT."""
        prompt = self._create_rule_extraction_prompt(text, document_type)
        
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert legal document analyzer specializing in extracting business rules and key terms from contracts and policies."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content, "openai")
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            raise e
    
    async def _generate_rules_google(self, text: str, document_type: str) -> Dict[str, Any]:
        """Generate rules using Google Gemini."""
        prompt = self._create_rule_extraction_prompt(text, document_type)
        
        try:
            response = self.google_model.generate_content(prompt)
            content = response.text
            return self._parse_ai_response(content, "google")
            
        except Exception as e:
            print(f"Google AI API error: {str(e)}")
            raise e
    
    def _create_rule_extraction_prompt(self, text: str, document_type: str) -> str:
        """Create a prompt for rule extraction."""
        base_prompt = f"""
        Analyze the following {document_type} and extract business rules in JSON format.

        Extract the following information:
        1. Key Obligations - What each party must do
        2. Restrictions - What each party cannot do  
        3. Conditions - When certain rules apply
        4. Deadlines - Time-based requirements
        5. Financial Terms - Payment, fees, penalties
        6. Termination Rules - How the agreement can end
        7. Key Definitions - Important terms defined

        Return the response in this JSON structure:
        {{
            "obligations": [
                {{"party": "Party Name", "obligation": "Description", "section": "Section reference if available"}}
            ],
            "restrictions": [
                {{"party": "Party Name", "restriction": "Description", "section": "Section reference if available"}}
            ],
            "conditions": [
                {{"condition": "If/when condition", "consequence": "Then this happens", "section": "Section reference if available"}}
            ],
            "deadlines": [
                {{"description": "Deadline description", "timeframe": "Time period", "section": "Section reference if available"}}
            ],
            "financial_terms": [
                {{"type": "payment/fee/penalty", "amount": "Amount if specified", "description": "Description", "section": "Section reference if available"}}
            ],
            "termination_rules": [
                {{"trigger": "What triggers termination", "notice_period": "Required notice", "section": "Section reference if available"}}
            ],
            "key_definitions": [
                {{"term": "Term", "definition": "Definition", "section": "Section reference if available"}}
            ]
        }}

        Document text:
        {text[:3000]}  # Limit text to avoid token limits
        
        Please provide only the JSON response without additional commentary.
        """
        
        return base_prompt
    
    def _parse_ai_response(self, content: str, provider: str) -> Dict[str, Any]:
        """Parse AI response and ensure valid JSON structure."""
        try:
            # Try to extract JSON from the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                parsed_rules = json.loads(json_str)
                
                # Validate structure
                expected_keys = ['obligations', 'restrictions', 'conditions', 'deadlines', 'financial_terms', 'termination_rules', 'key_definitions']
                for key in expected_keys:
                    if key not in parsed_rules:
                        parsed_rules[key] = []
                
                parsed_rules['provider'] = provider
                parsed_rules['extraction_method'] = 'ai_generated'
                return parsed_rules
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            # Return a basic structure with the raw content
            return {
                "obligations": [],
                "restrictions": [],
                "conditions": [],
                "deadlines": [],
                "financial_terms": [],
                "termination_rules": [],
                "key_definitions": [],
                "provider": provider,
                "extraction_method": "ai_generated",
                "raw_response": content[:1000],  # Store truncated raw response
                "error": f"Failed to parse response: {str(e)}"
            }
    
    async def _generate_rules_fallback(self, text: str, document_type: str) -> Dict[str, Any]:
        """Fallback rule extraction using pattern matching."""
        rules = {
            "obligations": [],
            "restrictions": [],
            "conditions": [],
            "deadlines": [],
            "financial_terms": [],
            "termination_rules": [],
            "key_definitions": [],
            "provider": "pattern_matching",
            "extraction_method": "fallback"
        }
        
        text_lower = text.lower()
        sentences = text.split('.')
        
        # Simple pattern matching for different rule types
        obligation_patterns = ['shall', 'must', 'required to', 'agrees to', 'undertakes to']
        restriction_patterns = ['shall not', 'may not', 'prohibited', 'forbidden', 'cannot']
        condition_patterns = ['if', 'when', 'unless', 'provided that', 'in the event']
        deadline_patterns = ['within', 'by', 'no later than', 'before', 'after']
        financial_patterns = ['pay', 'payment', 'fee', 'cost', 'price', '$', 'dollar']
        termination_patterns = ['terminate', 'termination', 'end', 'expire', 'cancel']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
                
            sentence_lower = sentence.lower()
            
            # Check for obligations
            if any(pattern in sentence_lower for pattern in obligation_patterns):
                rules['obligations'].append({
                    "party": "To be determined",
                    "obligation": sentence,
                    "section": "Pattern matched"
                })
            
            # Check for restrictions
            if any(pattern in sentence_lower for pattern in restriction_patterns):
                rules['restrictions'].append({
                    "party": "To be determined", 
                    "restriction": sentence,
                    "section": "Pattern matched"
                })
            
            # Check for conditions
            if any(pattern in sentence_lower for pattern in condition_patterns):
                rules['conditions'].append({
                    "condition": sentence,
                    "consequence": "To be determined",
                    "section": "Pattern matched"
                })
            
            # Check for deadlines
            if any(pattern in sentence_lower for pattern in deadline_patterns):
                rules['deadlines'].append({
                    "description": sentence,
                    "timeframe": "To be determined",
                    "section": "Pattern matched"
                })
            
            # Check for financial terms
            if any(pattern in sentence_lower for pattern in financial_patterns):
                rules['financial_terms'].append({
                    "type": "To be determined",
                    "amount": "To be determined",
                    "description": sentence,
                    "section": "Pattern matched"
                })
            
            # Check for termination rules
            if any(pattern in sentence_lower for pattern in termination_patterns):
                rules['termination_rules'].append({
                    "trigger": sentence,
                    "notice_period": "To be determined",
                    "section": "Pattern matched"
                })
        
        # Limit results to avoid overwhelming output
        for key in rules:
            if isinstance(rules[key], list) and len(rules[key]) > 5:
                rules[key] = rules[key][:5]
        
        return rules