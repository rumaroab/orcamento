"""LLM client for budget item extraction, categorization, and explanation."""
import json
from typing import List
from loguru import logger
from app.config import settings
from app.schemas import ExtractResponse, ExtractedItem
from app.models import SideEnum, CategoryEnum
from app.llm.providers import create_provider, LLMProvider


class LLMClient:
    """Client for LLM operations - provider-agnostic interface."""
    
    def __init__(self):
        """Initialize LLM client with the configured provider."""
        # Determine which provider to use
        if settings.LLM_DISABLED:
            provider_type = "disabled"
            logger.info("LLM_DISABLED=true, using disabled provider")
        else:
            provider_type = settings.LLM_PROVIDER.lower()
            logger.info(f"Using LLM provider: {provider_type}")
        
        # Create provider based on configuration
        if provider_type == "openai":
            self.provider = create_provider(
                "openai",
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            )
        elif provider_type == "ollama":
            self.provider = create_provider(
                "ollama",
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                use_chat_api=settings.OLLAMA_USE_CHAT_API
            )
        elif provider_type == "disabled":
            self.provider = create_provider("disabled")
        else:
            logger.warning(f"Unknown provider '{provider_type}', falling back to disabled")
            self.provider = create_provider("disabled")
        
        # Log provider availability
        if hasattr(self.provider, 'is_available'):
            if self.provider.is_available():
                logger.info(f"LLM provider '{provider_type}' is available")
            else:
                logger.warning(f"LLM provider '{provider_type}' is not available")
    
    def _call_with_retry(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """
        Call LLM provider with retries.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_retries: Maximum number of retries
            
        Returns:
            Response text
        """
        return self.provider.call(prompt, system_prompt, max_retries)
    
    def extract_items(self, title_path: str, pages_text: str) -> List[ExtractedItem]:
        """
        Extract budget items from text using LLM.
        
        Args:
            title_path: Section breadcrumb path (e.g., "L1 > L2 > L3")
            pages_text: Text from pages with markers like "--- PAGE 12 ---\n...text..."
            
        Returns:
            List of extracted items
        """
        system_prompt = """Você é um analisador de documentos orçamentais muito experiente. Extraia itens de linha orçamental do texto fornecido.
        REGRAS CRÍTICAS:
        1. Produza APENAS JSON válido correspondendo a este esquema exato:
        {
        "items": [
            {
            "side": "REVENUE" ou "EXPENSE",
            "descriptionOriginal": "texto exato do documento",
            "value": número ou null (NÃO invente números, use null se incerto),
            "unit": "EUR" ou "THOUSAND_EUR" ou "MILLION_EUR" ou "UNKNOWN",
            "pageNumber": número (a página onde evidenceText aparece),
            "evidenceText": "excerto literal do texto de entrada (50-200 caracteres)"
            }
        ]
        }

        2. NÃO calcule totais nem invente números. Extraia apenas o que vê.
        3. Se um valor não estiver claro ou faltar, defina value como null.
        4. evidenceText deve ser um excerto literal da entrada (copie e cole, não parafraseie).
        5. pageNumber deve corresponder ao marcador de página na entrada (ex: se a evidência está após "--- PAGE 12 ---", use 12).
        6. side deve ser REVENUE ou EXPENSE com base no contexto.
        7. Extraia TODOS os itens orçamentais que encontrar, mesmo que o valor seja null.
        8. IMPORTANTE: Todas as descrições e textos devem estar em português.
        """
        
        user_prompt = f"""Secção: {title_path}
        {pages_text}
        Extraia todos os itens de linha orçamental do texto acima. Retorne apenas JSON, sem outro texto."""
                
        try:
            response_text = self._call_with_retry(user_prompt, system_prompt)
            
            if settings.LLM_DISABLED or not response_text:
                # Return empty list in dry-run mode or if provider returned empty
                return []
            
            # Parse JSON response
            # Sometimes LLM wraps JSON in markdown code blocks
            response_text = response_text.strip()
            if response_text.startswith("```"):
                # Remove markdown code block markers
                lines = response_text.split('\n')
                # Find the closing ```
                closing_idx = -1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith("```"):
                        closing_idx = i
                        break
                if closing_idx > 0:
                    response_text = '\n'.join(lines[1:closing_idx])
                else:
                    response_text = '\n'.join(lines[1:])
            
            # Try to extract JSON if wrapped in other text
            # Look for JSON object boundaries
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx >= 0 and end_idx > start_idx:
                response_text = response_text[start_idx:end_idx + 1]
            
            data = json.loads(response_text)
            extract_response = ExtractResponse(**data)
            
            logger.info(f"Extracted {len(extract_response.items)} items from section {title_path}")
            return extract_response.items
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error extracting items: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            # Return empty list on error (don't fail the whole job)
            return []
        except Exception as e:
            logger.error(f"Error extracting items: {e}")
            # Return empty list on error (don't fail the whole job)
            return []
    
    def categorize_item(self, side: SideEnum, title_path: str, description: str) -> CategoryEnum:
        """
        Categorize a budget item into the simple taxonomy.
        
        Args:
            side: REVENUE or EXPENSE
            title_path: Section breadcrumb path
            description: Original description text
            
        Returns:
            Category enum value
        """
        if settings.LLM_DISABLED:
            # Return a default category in dry-run mode
            return CategoryEnum.OTHER_REVENUE if side == SideEnum.REVENUE else CategoryEnum.INFRASTRUCTURE_ENVIRONMENT
        
        # Define allowed categories based on side (in Portuguese)
        if side == SideEnum.REVENUE:
            allowed = [
                "Impostos sobre pessoas",
                "Impostos sobre empresas",
                "Impostos sobre compras",
                "Contribuições para segurança social",
                "Outras receitas"
            ]
        else:
            allowed = [
                "Saúde",
                "Educação",
                "Pensões e apoio social",
                "Funcionamento do governo",
                "Segurança e defesa",
                "Justiça",
                "Infraestrutura e ambiente",
                "Dívida pública"
            ]
        
        system_prompt = f"""
        Você é um categorizador de orçamento. Atribua cada item a exatamente uma categoria da lista permitida.

        Lado: {"RECEITA" if side == SideEnum.REVENUE else "DESPESA"}
        Categorias permitidas: {', '.join(allowed)}

        Retorne APENAS o nome exato da categoria da lista permitida, nada mais.
        IMPORTANTE: Retorne o nome da categoria em português exatamente como aparece na lista.
        """
                
        user_prompt = f"""
        Secção: {title_path}
        Descrição: {description}

        Categorize este item orçamental. Retorne apenas o nome da categoria que mais se relaciona em português.
        """
                
        try:
            response_text = self._call_with_retry(user_prompt, system_prompt).strip()
            
            # Map response to enum - try exact match first
            response_clean = response_text.strip()
            for cat in CategoryEnum:
                if cat.value == response_clean:
                    logger.info(f"Categorized item as {cat.value}")
                    return cat
            
            # If no exact match, try case-insensitive
            for cat in CategoryEnum:
                if cat.value.lower() == response_clean.lower():
                    logger.info(f"Categorized item as {cat.value} (case-insensitive match)")
                    return cat
            
            # Default fallback
            logger.warning(f"Could not match category '{response_text}', using default")
            if side == SideEnum.REVENUE:
                return CategoryEnum.OTHER_REVENUE
            else:
                return CategoryEnum.INFRASTRUCTURE_ENVIRONMENT
                
        except Exception as e:
            logger.error(f"Error categorizing item: {e}")
            # Return default category on error
            if side == SideEnum.REVENUE:
                return CategoryEnum.OTHER_REVENUE
            else:
                return CategoryEnum.INFRASTRUCTURE_ENVIRONMENT
    
    def explain_item(self, title_path: str, evidence_text: str) -> str:
        """
        Generate a 2-3 sentence explanation for a budget item.
        
        Args:
            title_path: Section breadcrumb path
            evidence_text: Literal excerpt from document
            
        Returns:
            Explanation text (2-3 sentences)
        """
        if settings.LLM_DISABLED:
            return f"This item appears in section {title_path}. Evidence: {evidence_text[:100]}..."
        
        system_prompt = """Você é um explicador de documentos orçamentais. Gere explicações claras e factuais para itens orçamentais.

        REGRAS:
        1. Escreva apenas 2-3 frases.
        2. Baseie a explicação APENAS no texto de evidência e no contexto da secção.
        3. NÃO adicione opiniões políticas ou especulação.
        4. NÃO invente números além do que está na evidência.
        5. Use linguagem simples que cidadãos comuns possam entender.
        6. Seja factual e neutro.
        7. IMPORTANTE: Escreva sempre em português."""
                
        user_prompt = f"""Secção: {title_path}
        Evidência: {evidence_text}

        Explique este item orçamental em 2-3 frases para cidadãos comuns. Escreva em português."""
                
        try:
            explanation = self._call_with_retry(user_prompt, system_prompt).strip()
            logger.info(f"Generated explanation (length: {len(explanation)})")
            return explanation
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return f"This item appears in section {title_path}. Evidence: {evidence_text[:200]}..."


# Global client instance
llm_client = LLMClient()

