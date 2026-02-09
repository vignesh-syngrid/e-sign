import re
from typing import Dict, List, Optional

# Uncomment when running with network access
# from langchain_community.llms import HuggingFaceHub
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain


class LLMService:
    """Service for interacting with LLM to analyze documents"""
    
    def __init__(self):
        """
        Initialize the LLM service
        Note: Requires HUGGINGFACEHUB_API_TOKEN environment variable
        Get free token from: https://huggingface.co/settings/tokens
        """
        # Uncomment when running with network access:
        # self.llm = HuggingFaceHub(
        #     repo_id="google/flan-t5-large",  # Free model
        #     model_kwargs={"temperature": 0.7, "max_length": 512}
        # )
        pass
    
    def analyze_document_for_signature(self, text: str, page_number: int = 1) -> Dict:
        """
        Analyze document text to suggest where signature should be placed
        
        Args:
            text: Extracted text from document
            page_number: Page number being analyzed
            
        Returns:
            Dictionary with suggested position and reasoning
        """
        # Rule-based approach (works offline without LLM)
        suggestions = self._rule_based_analysis(text, page_number)
        
        # Uncomment for LLM-based analysis when network is available:
        # llm_suggestions = self._llm_based_analysis(text, page_number)
        # suggestions.update(llm_suggestions)
        
        return suggestions
    
    def _rule_based_analysis(self, text: str, page_number: int) -> Dict:
        """
        Rule-based signature placement suggestion
        """
        text_lower = text.lower()
        suggestions = {
            'suggested_page': page_number,
            'suggested_x': 100,  # Default X position
            'suggested_y': 100,  # Default Y position
            'confidence': 'medium',
            'reasoning': 'Default signature placement at bottom of document'
        }
        
        # Look for common signature keywords
        signature_keywords = [
            r'signature[\s:]*[_\s]*',
            r'sign[\s]*here',
            r'signed[\s:]*',
            r'authorized[\s]*by',
            r'signatory',
            r'undersigned',
            r'date[\s]*[_\s]*signature'
        ]
        
        for keyword in signature_keywords:
            if re.search(keyword, text_lower):
                suggestions['confidence'] = 'high'
                suggestions['reasoning'] = f'Found signature indicator: "{keyword}"'
                # Suggest bottom-right for signature fields
                suggestions['suggested_x'] = 400
                suggestions['suggested_y'] = 650
                break
        
        # Check for date fields (signatures often near dates)
        date_patterns = [
            r'date[\s:]*[_\s]*',
            r'dated[\s]*this',
            r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text_lower):
                suggestions['has_date_field'] = True
                suggestions['reasoning'] += ' | Document contains date field near signature area'
        
        # Look for agreement/contract indicators
        agreement_keywords = ['agreement', 'contract', 'terms and conditions', 'hereby agree']
        if any(keyword in text_lower for keyword in agreement_keywords):
            suggestions['document_type'] = 'agreement'
            suggestions['suggested_y'] = 700  # Bottom of page for agreements
        
        return suggestions
    
    def _llm_based_analysis(self, text: str, page_number: int) -> Dict:
        """
        LLM-based signature placement suggestion (requires network)
        """
        # Uncomment when running with network access:
        
        # prompt_template = """
        # Analyze the following document text and suggest where a signature should be placed.
        # Consider:
        # 1. Signature lines or placeholders
        # 2. Date fields
        # 3. Document type (contract, agreement, letter, etc.)
        # 4. Legal or formal language indicating signature requirement
        # 
        # Document text:
        # {text}
        # 
        # Provide your analysis in the following format:
        # - Document Type: [type]
        # - Signature Needed: [yes/no]
        # - Suggested Location: [description]
        # - Reasoning: [explanation]
        # """
        # 
        # prompt = PromptTemplate(template=prompt_template, input_variables=["text"])
        # chain = LLMChain(llm=self.llm, prompt=prompt)
        # 
        # response = chain.run(text=text[:2000])  # Limit text length
        # 
        # return {
        #     'llm_analysis': response,
        #     'llm_confidence': 'high'
        # }
        
        return {
            'llm_analysis': 'LLM analysis disabled (offline mode)',
            'llm_confidence': 'N/A'
        }
    
    def extract_key_information(self, text: str) -> Dict:
        """
        Extract key information from document that might be useful
        """
        info = {
            'has_signature_field': False,
            'has_date_field': False,
            'document_length': len(text),
            'key_terms': []
        }
        
        # Check for signature field
        if re.search(r'signature|sign here|signatory', text.lower()):
            info['has_signature_field'] = True
        
        # Check for date field
        if re.search(r'date[\s:]*|dated|_____/_____/_____', text.lower()):
            info['has_date_field'] = True
        
        # Extract potential key terms
        important_terms = ['agreement', 'contract', 'party', 'undersigned', 'witness']
        info['key_terms'] = [term for term in important_terms if term in text.lower()]
        
        return info


# Helper function to initialize LLM service
def get_llm_service():
    """Factory function to get LLM service instance"""
    return LLMService()