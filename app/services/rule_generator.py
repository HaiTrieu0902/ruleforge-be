from groq import Groq
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from typing import Dict, List, Any
from app.core.config import settings

class RuleGenerator:
    """Service for generating business rules from contracts using Groq AI."""
    
    def __init__(self):
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq AI client."""
        try:
            print(f"🔧 Initializing Groq client for rule generation...")
            print(f"🔑 API Key configured: {'Yes' if settings.groq_api_key and len(settings.groq_api_key) > 10 else 'No'}")
            print(f"🤖 Model: {settings.groq_model}")
            
            if not settings.groq_api_key:
                raise Exception("Groq API key not configured. Please set GROQ_API_KEY in your .env file")
            
            self.client = Groq(api_key=settings.groq_api_key)
            self.model = settings.groq_model
            print(f"✅ Groq client initialized successfully for rule generation")
            
        except Exception as e:
            print(f"❌ Failed to initialize Groq client: {str(e)}")
            raise
    
    async def generate_rules(self, text: str, document_type: str = "contract") -> Dict[str, Any]:
        """Generate business rules from document text using Groq AI."""
        try:
            if self.client:
                return await self._generate_rules_groq(text, document_type)
            else:
                # Fallback to simple pattern-based rule extraction
                return await self._generate_rules_fallback(text, document_type)
                
        except Exception as e:
            print(f"Error generating rules: {str(e)}")
            return await self._generate_rules_fallback(text, document_type)
    
    def _detect_language_instruction(self, text: str) -> str:
        """Detect the language of the text and provide appropriate instruction."""
        # Common Vietnamese words and patterns
        vietnamese_indicators = [
            'và', 'của', 'là', 'có', 'được', 'cho', 'từ', 'trong', 'với', 'các', 
            'này', 'đó', 'để', 'những', 'một', 'về', 'theo', 'như', 'đã', 'sẽ',
            'tại', 'do', 'khi', 'mà', 'nếu', 'hoặc', 'nhưng', 'vì', 'bởi', 'thì',
            'ở', 'trên', 'dưới', 'giữa', 'sau', 'trước', 'ngoài', 'trong'
        ]
        
        # Convert to lowercase for comparison
        text_lower = text.lower()
        
        # Count Vietnamese indicators
        vietnamese_count = sum(1 for word in vietnamese_indicators if f' {word} ' in text_lower or text_lower.startswith(f'{word} ') or text_lower.endswith(f' {word}'))
        
        # Check for Vietnamese specific characters
        vietnamese_chars = ['ă', 'â', 'đ', 'ê', 'ô', 'ơ', 'ư', 'á', 'à', 'ả', 'ã', 'ạ', 'é', 'è', 'ẻ', 'ẽ', 'ẹ', 'í', 'ì', 'ỉ', 'ĩ', 'ị', 'ó', 'ò', 'ỏ', 'õ', 'ọ', 'ú', 'ù', 'ủ', 'ũ', 'ụ', 'ý', 'ỳ', 'ỷ', 'ỹ', 'ỵ']
        has_vietnamese_chars = any(char in text_lower for char in vietnamese_chars)
        
        print(f"🔍 Language detection for rules - Vietnamese words: {vietnamese_count}, Vietnamese chars: {has_vietnamese_chars}")
        
        # Determine language based on indicators
        if vietnamese_count > 3 or has_vietnamese_chars:
            return "IMPORTANT: Please respond in Vietnamese language (tiếng Việt). The document is in Vietnamese, so all rules and explanations must be in Vietnamese."
        else:
            return "Please respond in English."

    async def _generate_rules_groq(self, text: str, document_type: str) -> Dict[str, Any]:
        """Generate rules using Groq AI."""
        try:
            # Detect language and create appropriate prompt
            language_instruction = self._detect_language_instruction(text)
            prompt = self._create_rule_extraction_prompt(text, document_type, language_instruction)
            
            print(f"🔄 Sending rule extraction request to Groq API with model: {self.model}")
            print(f"📝 Text length: {len(text)} characters")
            
            # Use thread executor to make the blocking call async
            completion = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert legal document analyzer specializing in extracting business rules and key terms from contracts and policies. You can work with documents in both Vietnamese and English languages."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                    top_p=1,
                    stream=False,
                    stop=None
                )
            )
            
            print(f"✅ Received rule extraction response from Groq API")
            
            if completion and hasattr(completion, 'choices') and completion.choices and len(completion.choices) > 0:
                if hasattr(completion.choices[0], 'message') and hasattr(completion.choices[0].message, 'content'):
                    content = completion.choices[0].message.content
                    if content:
                        content = content.strip()
                        print(f"✅ Rules generated: {len(content)} characters")
                        return self._parse_ai_response(content, "groq")
                    else:
                        print("❌ Rule extraction content is empty")
                        return await self._generate_rules_fallback(text, document_type)
                else:
                    print("❌ Invalid response structure from Groq API")
                    return await self._generate_rules_fallback(text, document_type)
            else:
                print("❌ No choices returned from Groq API")
                return await self._generate_rules_fallback(text, document_type)
                
        except Exception as e:
            print(f"❌ Error in Groq API call for rule generation: {str(e)}")
            print(f"❌ Error type: {type(e).__name__}")
            return await self._generate_rules_fallback(text, document_type)
    
    def _create_rule_extraction_prompt(self, text: str, document_type: str, language_instruction: str) -> str:
        """Create a prompt for rule extraction."""
        base_prompt = f"""
        Analyze the following {document_type} and extract business rules in a structured conditional format.
        {language_instruction}

        Create business rules using this structured format:
        
        <if> CONDITION
            <and> ADDITIONAL_CONDITION
            <or> ALTERNATIVE_CONDITION
            <thn> ACTION_TO_TAKE
        <elif> DIFFERENT_CONDITION
            <thn> DIFFERENT_ACTION
        <else>
            <thn> DEFAULT_ACTION

        Example format:
        <if> APPLICANT_AGE > 18
            <and> WORK_EXPERIENCE > 12
            <and> LOAN_END_DATE > RETIREMENT_DATE
                <if> EARLY_RETIREMENT = True
                    <and> INCOME_VERIFIED = 1
                    <thn> INCOME_RECORD = INCOME_RECORD * REFERENCE_SALARY
                <elif> EARLY_RETIREMENT = False
                    <if> INSURANCE_PROOF = True
                        <and> INSURANCE_DURATION >= 3
                        <thn> INCOME_RECORD = SALARY_RECORD * INSURANCE_SALARY
                    <else>
                        <thn> INCOME_RECORD = 0

        Extract and convert contract terms into this format. Focus on:
        1. Eligibility conditions (age, experience, qualifications)
        2. Payment conditions (amounts, timing, methods)
        3. Approval/rejection logic
        4. Penalty calculations
        5. Termination conditions
        6. Compliance requirements

        Return the response in this JSON structure:
        {{
            "business_rules": [
                {{
                    "rule_id": "RULE_001",
                    "rule_name": "Descriptive name",
                    "rule_logic": "Complete rule in structured format",
                    "category": "eligibility/payment/approval/penalty/termination/compliance",
                    "variables_used": ["VAR1", "VAR2", "VAR3"],
                    "description": "What this rule does"
                }}
            ],
            "variables": [
                {{
                    "variable_name": "VARIABLE_NAME",
                    "data_type": "number/string/boolean/date",
                    "description": "What this variable represents",
                    "possible_values": ["value1", "value2"] 
                }}
            ],
            "constants": [
                {{
                    "constant_name": "CONSTANT_NAME",
                    "value": "actual_value",
                    "description": "What this constant represents"
                }}
            ]
        }}

        Document text:
        {text[:4000]}
        
        Please provide only the JSON response without additional commentary.
        Convert all contract conditions into structured business rules using the <if><and><or><thn><elif><else> format.
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
                
                # Validate new structure
                expected_keys = ['business_rules', 'variables', 'constants']
                for key in expected_keys:
                    if key not in parsed_rules:
                        parsed_rules[key] = []
                
                # Ensure business_rules have required fields
                if parsed_rules.get('business_rules'):
                    for rule in parsed_rules['business_rules']:
                        if 'rule_id' not in rule:
                            rule['rule_id'] = f"RULE_{len(parsed_rules['business_rules'])}"
                        if 'rule_name' not in rule:
                            rule['rule_name'] = "Generated Rule"
                        if 'category' not in rule:
                            rule['category'] = "general"
                        if 'variables_used' not in rule:
                            rule['variables_used'] = []
                
                parsed_rules['provider'] = provider
                parsed_rules['extraction_method'] = 'ai_generated'
                parsed_rules['rule_format'] = 'structured_conditional'
                return parsed_rules
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            # Return a basic structure with the raw content
            return {
                "business_rules": [],
                "variables": [],
                "constants": [],
                "provider": provider,
                "extraction_method": "ai_generated",
                "rule_format": "structured_conditional",
                "raw_response": content[:1000],  # Store truncated raw response
                "error": f"Failed to parse response: {str(e)}"
            }
    
    async def _generate_rules_fallback(self, text: str, document_type: str) -> Dict[str, Any]:
        """Fallback rule extraction using pattern matching."""
        rules = {
            "business_rules": [],
            "variables": [],
            "constants": [],
            "provider": "pattern_matching",
            "extraction_method": "fallback",
            "rule_format": "structured_conditional"
        }
        
        text_lower = text.lower()
        sentences = text.split('.')
        rule_counter = 1
        
        # Simple pattern matching for different rule types
        obligation_patterns = ['shall', 'must', 'required to', 'agrees to', 'undertakes to']
        restriction_patterns = ['shall not', 'may not', 'prohibited', 'forbidden', 'cannot']
        condition_patterns = ['if', 'when', 'unless', 'provided that', 'in the event']
        deadline_patterns = ['within', 'by', 'no later than', 'before', 'after']
        financial_patterns = ['pay', 'payment', 'fee', 'cost', 'price', '$', 'dollar', 'vnd', 'đồng']
        termination_patterns = ['terminate', 'termination', 'end', 'expire', 'cancel']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
                
            sentence_lower = sentence.lower()
            
            # Check for obligations and convert to structured format
            if any(pattern in sentence_lower for pattern in obligation_patterns):
                rule_logic = f"<if> PARTY_TYPE = 'OBLIGATED'\n    <thn> ACTION_REQUIRED = '{sentence}'"
                rules['business_rules'].append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "rule_name": f"Obligation Rule {rule_counter}",
                    "rule_logic": rule_logic,
                    "category": "obligation",
                    "variables_used": ["PARTY_TYPE", "ACTION_REQUIRED"],
                    "description": f"Obligation requirement: {sentence[:100]}..."
                })
                rule_counter += 1
            
            # Check for restrictions
            if any(pattern in sentence_lower for pattern in restriction_patterns):
                rule_logic = f"<if> PARTY_TYPE = 'RESTRICTED'\n    <thn> ACTION_FORBIDDEN = '{sentence}'"
                rules['business_rules'].append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "rule_name": f"Restriction Rule {rule_counter}",
                    "rule_logic": rule_logic,
                    "category": "restriction",
                    "variables_used": ["PARTY_TYPE", "ACTION_FORBIDDEN"],
                    "description": f"Restriction requirement: {sentence[:100]}..."
                })
                rule_counter += 1
            
            # Check for conditions
            if any(pattern in sentence_lower for pattern in condition_patterns):
                rule_logic = f"<if> CONDITION_MET = True\n    <thn> CONSEQUENCE = '{sentence}'"
                rules['business_rules'].append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "rule_name": f"Conditional Rule {rule_counter}",
                    "rule_logic": rule_logic,
                    "category": "condition",
                    "variables_used": ["CONDITION_MET", "CONSEQUENCE"],
                    "description": f"Conditional requirement: {sentence[:100]}..."
                })
                rule_counter += 1
            
            # Check for financial terms
            if any(pattern in sentence_lower for pattern in financial_patterns):
                rule_logic = f"<if> PAYMENT_DUE = True\n    <thn> AMOUNT_CALCULATION = '{sentence}'"
                rules['business_rules'].append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "rule_name": f"Financial Rule {rule_counter}",
                    "rule_logic": rule_logic,
                    "category": "payment",
                    "variables_used": ["PAYMENT_DUE", "AMOUNT_CALCULATION"],
                    "description": f"Financial requirement: {sentence[:100]}..."
                })
                rule_counter += 1
        
        # Add some common variables
        rules['variables'] = [
            {
                "variable_name": "PARTY_TYPE",
                "data_type": "string",
                "description": "Type of party in the contract",
                "possible_values": ["BUYER", "SELLER", "OBLIGATED", "RESTRICTED"]
            },
            {
                "variable_name": "CONDITION_MET",
                "data_type": "boolean",
                "description": "Whether a specific condition is satisfied",
                "possible_values": ["True", "False"]
            },
            {
                "variable_name": "PAYMENT_DUE",
                "data_type": "boolean",
                "description": "Whether payment is required",
                "possible_values": ["True", "False"]
            }
        ]
        
        # Limit results to avoid overwhelming output
        if len(rules['business_rules']) > 10:
            rules['business_rules'] = rules['business_rules'][:10]
        
        return rules
    
    def close(self):
        """Clean up resources."""
        if self.executor:
            self.executor.shutdown(wait=True)