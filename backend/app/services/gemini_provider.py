"""Gemini implementation of the LLM provider."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ..config import AppSettings, settings
from ..models import ChatMessage, RetrievedProduct
from .llm_types import LLMProductRecommendation, LLMProvider, LLMResult


logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini 2.5 Pro backed LLM provider."""

    def __init__(self, app_settings: Optional[AppSettings] = None) -> None:
        self.settings = app_settings or settings
        self._offline_mode = not self.settings.gemini_api_key
        self._model: Optional[genai.GenerativeModel] = None
        self._streaming_model: Optional[genai.GenerativeModel] = None
        self._model_name: Optional[str] = None
        self._fallback_model_name = "gemini-2.5-flash"

        if not self._offline_mode:
            try:
                genai.configure(api_key=self.settings.gemini_api_key)
                self._model = self._initialise_model(self.settings.llm_model, use_json_mode=True)
                self._streaming_model = self._initialise_model(self.settings.llm_model, use_json_mode=False)
                if self._model:
                    logger.info("Initialized Gemini models: %s (JSON + streaming)", self._model_name)
                else:
                    logger.warning("Gemini model initialisation returned None; entering offline mode.")
                    self._offline_mode = True
            except Exception as exc:
                logger.error("Failed to initialize Gemini: %s", exc, exc_info=True)
                self._offline_mode = True

    # ----------------------------------------------------------------- public api
    async def generate_response(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        if self._offline_mode or not self._model:
            return self._offline_response(messages, context_products)

        loop = asyncio.get_running_loop()
        raw_response = await loop.run_in_executor(
            None,
            self._generate_sync,
            list(messages),
            list(context_products),
        )
        parsed = self.parse_response_text(raw_response or "", context_products)
        if not parsed.reply.strip():
            return self._offline_response(messages, context_products)
        return parsed

    async def stream_response(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> AsyncIterator[str]:
        if self._offline_mode or not self._streaming_model:
            yield self._offline_response(messages, context_products).reply
            return

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        history, final_message = self._prepare_gemini_history(messages, context_products)

        def _worker() -> None:
            try:
                chat = self._streaming_model.start_chat(history=history)
                stream = chat.send_message(final_message, stream=True)
            except google_exceptions.ResourceExhausted as exc:
                if self._model_name != self._fallback_model_name:
                    logger.warning("Gemini streaming quota exhausted (%s); retrying with fallback model.", exc)
                    self._streaming_model = self._initialise_model(self._fallback_model_name, use_json_mode=False)
                    chat = self._streaming_model.start_chat(history=history)
                    stream = chat.send_message(final_message, stream=True)
                else:
                    logger.error("Gemini streaming quota exhausted with no fallback.", exc_info=True)
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                    return
            except Exception as exc:
                logger.error("Gemini streaming failed: %s", exc, exc_info=True)
                loop.call_soon_threadsafe(queue.put_nowait, None)
                return

            for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
            loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _worker)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    # ----------------------------------------------------------------- generation
    def _generate_sync(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> str:
        history, final_message = self._prepare_gemini_history(messages, context_products)
        logger.debug(
            "Sending Gemini request model=%s history_len=%d final_len=%d",
            self._model_name,
            len(history),
            len(final_message),
        )
        chat = self._model.start_chat(history=history)
        try:
            response = chat.send_message(final_message)
        except google_exceptions.ResourceExhausted as exc:
            if self._model_name != self._fallback_model_name:
                logger.warning("Gemini quota exhausted (%s); retrying with fallback model.", exc)
                self._model = self._initialise_model(self._fallback_model_name)
                chat = self._model.start_chat(history=history)
                response = chat.send_message(final_message)
            else:
                logger.error("Gemini quota exhausted with no fallback available.", exc_info=True)
                raise exc
        except Exception as exc:
            logger.error("Gemini send_message failed: %s", exc, exc_info=True)
            raise
        text = self._extract_text(response)
        if not text and self._model_name != self._fallback_model_name:
            logger.warning("Gemini returned empty text; retrying with fallback model.")
            self._model = self._initialise_model(self._fallback_model_name)
            chat = self._model.start_chat(history=history)
            response = chat.send_message(final_message)
            text = self._extract_text(response)
        logger.debug("Gemini response length=%d", len(text) if text else 0)
        return text

    def _prepare_gemini_history(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> tuple[List[Dict[str, Any]], str]:
        if not messages:
            raise ValueError("Conversation history cannot be empty.")

        formatted_history: List[Dict[str, Any]] = []
        for message in messages[:-1]:
            role = "model" if message.role == "assistant" else message.role
            formatted_history.append({"role": role, "parts": [message.content]})

        context_block = self._format_product_context(context_products)
        last_message = messages[-1]
        final_message = last_message.content
        if context_block:
            final_message = (
                f"{last_message.content}\n\n"
                f"Contextual product candidates:\n{context_block}\n"
                "Please respond following the JSON schema specified in the system prompt."
            )
        return formatted_history, final_message

    # ---------------------------------------------------------------------- parse
    def parse_response_text(
        self, text: str, context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        raw_text = text or ""
        if not raw_text:
            return LLMResult(reply="", reasoning=None, recommendations=[])

        # DEBUG: Log the raw LLM response
        logger.info("RAW LLM RESPONSE: %s", raw_text[:500])

        # Check if response is JSON or plain text
        raw_text_stripped = raw_text.strip()
        is_json = raw_text_stripped.startswith('{') and raw_text_stripped.endswith('}')

        if not is_json:
            # Plain text response from streaming - extract product mentions
            return self._parse_plain_text_response(raw_text, context_products)

        try:
            payload = json.loads(raw_text, strict=False)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1:
                snippet = raw_text[start : end + 1]
                try:
                    payload = json.loads(snippet, strict=False)
                except json.JSONDecodeError:
                    heuristic = self._heuristic_parse(raw_text, context_products)
                    if heuristic:
                        return heuristic
                    return self._fallback_result(raw_text, context_products)
            else:
                heuristic = self._heuristic_parse(raw_text, context_products)
                if heuristic:
                    return heuristic
                return self._fallback_result(raw_text, context_products)

        reply = (payload.get("reply") or "").strip()
        reasoning = payload.get("reasoning") or payload.get("analysis")
        recommendations_payload = payload.get("product_recommendations") or payload.get("recommendations") or []

        # DEBUG logging
        logger.info("DEBUG: reply_len=%s, reasoning_len=%s, rec_payload_len=%s, context_products_len=%s",
                   len(reply), len(reasoning or ""), len(recommendations_payload), len(list(context_products)))

        recommendations: List[LLMProductRecommendation] = []

        for item in recommendations_payload:
            sku = str(item.get("sku", "")).strip()
            if not sku:
                continue
            name = item.get("name") or self._product_name_for_sku(context_products, sku) or sku
            rationale = item.get("rationale") or item.get("reason") or ""
            confidence = item.get("confidence")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    confidence = None
            recommendations.append(
                LLMProductRecommendation(
                    sku=sku,
                    name=name,
                    rationale=rationale,
                    confidence=confidence,
                )
            )

        reply_is_question = "?" in reply
        reply_blocks_recommendations = self._reply_indicates_no_results(reply)

        # Only fallback when the reply appears to be making recommendations but failed to return structured data.
        # If the reply explicitly states there are no matching laptops (or asks a question), respect that.
        if (
            not recommendations
            and context_products
            and reply
            and not reply_is_question
            and not reply_blocks_recommendations
        ):
            logger.warning("LLM reply omitted product_recommendations; falling back to top matches.")
            default_products = list(context_products)[:2]
            recommendations = [
                LLMProductRecommendation(
                    sku=product.sku,
                    name=product.name,
                    rationale=product.explanation or "Top match based on your requirements.",
                )
                for product in default_products
            ]

        return LLMResult(reply=reply.strip(), reasoning=reasoning, recommendations=recommendations)

    @staticmethod
    def _reply_indicates_no_results(reply: str) -> bool:
        """Detect if the LLM explicitly says no products match the requirements."""
        if not reply:
            return False
        text = reply.lower()

        hard_clauses = [
            "no laptops",
            "no systems",
            "no options",
            "no matches",
            "no matching",
            "none of the laptops",
            "none of these laptops",
            "don't have any",
            "do not have any",
            "can't find any",
            "cannot find any",
            "couldn't find any",
            "unfortunately i don't have",
        ]
        if any(clause in text for clause in hard_clauses):
            return True

        soft_clauses = ["closest option is", "over your budget"]
        negative_tones = ["unfortunately", "sorry", "can't", "cannot", "don't", "do not", "no "]
        if any(clause in text for clause in soft_clauses) and any(token in text for token in negative_tones):
            return True

        return False

    def _fallback_result(
        self, raw_text: str, context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        default_products = list(context_products)[:2]
        recommendations = [
            LLMProductRecommendation(
                sku=product.sku,
                name=product.name,
                rationale=product.explanation or "Recommended based on similarity to your request.",
            )
            for product in default_products
        ]
        return LLMResult(reply=raw_text.strip(), reasoning=None, recommendations=recommendations)

    def _parse_plain_text_response(
        self, text: str, context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        """Parse plain text streaming response to extract product recommendations."""
        reply = text.strip()
        reply_lower = reply.lower()

        # Check if response is asking clarifying questions
        # A question ends with ? - if it's a question, it's NOT a recommendation
        is_question = '?' in reply

        if is_question:
            # LLM is asking for clarification - no products to show
            logger.info("Detected clarifying question in streaming response - no products")
            return LLMResult(reply=reply, reasoning="Asking for clarification", recommendations=[])

        # Check if LLM is making recommendations (contains recommendation keywords AND not a question)
        is_recommending = any(keyword in reply_lower for keyword in ['recommend', 'suggest', 'great choice', 'perfect for', 'ideal for', 'best option'])

        if not is_recommending:
            # General informational response - no products
            logger.info("No recommendation detected in streaming response")
            return LLMResult(reply=reply, reasoning=None, recommendations=[])

        # Extract mentioned product names from text
        mentioned_products: List[LLMProductRecommendation] = []
        text_lower = text.lower()

        for product in context_products:
            # Check if product name or key identifiers are mentioned
            product_name_lower = product.name.lower()

            # Check for full name match or significant parts
            name_parts = product_name_lower.split()
            # Filter out common words and keep significant parts
            significant_parts = [part for part in name_parts if len(part) > 3 and part not in ['laptop', 'notebook', 'the', 'and']]

            is_mentioned = False
            if product_name_lower in text_lower:
                is_mentioned = True
            elif len(significant_parts) >= 2:
                # Check if at least 2 significant parts are mentioned
                if all(part in text_lower for part in significant_parts[:2]):
                    is_mentioned = True
            elif len(significant_parts) == 1 and significant_parts[0] in text_lower:
                # For products with one distinctive name (e.g., "ThinkPad"), match on that
                is_mentioned = True

            if is_mentioned:
                mentioned_products.append(
                    LLMProductRecommendation(
                        sku=product.sku,
                        name=product.name,
                        rationale=f"Recommended in conversation",
                    )
                )

        # If products were mentioned, return up to 2
        if mentioned_products:
            logger.info("Extracted %d product recommendations from streaming text", len(mentioned_products))
            return LLMResult(
                reply=reply,
                reasoning="Products extracted from conversational response",
                recommendations=mentioned_products[:2]
            )

        # LLM is recommending but we couldn't extract product names - return top 2 from context as fallback
        logger.warning("LLM recommending but no product names extracted - using top 2 from context")
        fallback_products = list(context_products)[:2]
        recommendations = [
            LLMProductRecommendation(
                sku=product.sku,
                name=product.name,
                rationale="Recommended based on your requirements",
            )
            for product in fallback_products
        ]
        return LLMResult(reply=reply, reasoning="Fallback recommendations", recommendations=recommendations)

    # ------------------------------------------------------------------- formatting
    def _streaming_system_prompt(self) -> str:
        """System prompt for streaming mode - outputs conversational text only."""
        return (
            "You are Automatiq.ai's expert laptop advisor. Your goal is to recommend the BEST product match through intelligent conversation.\n\n"
            "CRITICAL RULES - MUST FOLLOW:\n"
            "1. BUDGET CONSTRAINTS ARE ABSOLUTE:\n"
            "   - If user specifies a budget (e.g., 'under $1500', 'max $2000'), NEVER recommend products above it\n"
            "   - Extract the maximum price from phrases like 'under X', 'max X', 'below X'\n"
            "   - If NO products match the budget, explicitly tell the user and mention the closest option\n\n"
            "DECISION LOGIC:\n"
            "1. If the user's request is VAGUE or missing key details (use case, budget, performance needs):\n"
            "   - Ask 1-2 specific follow-up questions to clarify\n"
            "   - Keep your response to 2-3 sentences\n"
            "   - Example: 'What's your budget and what will you mainly use it for?'\n\n"
            "2. If you have ENOUGH information to make a confident recommendation:\n"
            "   - Recommend products from the context provided\n"
            "   - Give a brief 2-3 sentence explanation\n"
            "   - Mention specific product names from the context\n"
            "   - Focus on how each matches their specific needs\n\n"
            "STYLE GUIDELINES:\n"
            "- Be conversational and concise (max 3-4 sentences)\n"
            "- Match the user's tone (casual vs technical)\n"
            "- Only recommend from the provided product context\n"
            "- NEVER output JSON or structured data - just natural conversational text\n"
        )

    def _system_prompt(self) -> str:
        return (
            "You are Automatiq.ai's expert laptop advisor. Your goal is to recommend the BEST product match through intelligent conversation.\n\n"
            "CRITICAL RULES - MUST FOLLOW:\n"
            "1. BUDGET CONSTRAINTS ARE ABSOLUTE:\n"
            "   - If user specifies a budget (e.g., 'under $1500', 'max $2000', 'under 1400 usd'), NEVER recommend products above it\n"
            "   - ONLY recommend products from the provided context that fit WITHIN the stated budget\n"
            "   - Extract the maximum price from phrases like 'under X', 'max X', 'below X' and filter strictly\n"
            "   - If NO products in the context match the budget, you MUST:\n"
            "     a) Explicitly tell the user no laptops were found in their budget\n"
            "     b) Mention the closest option and how much it exceeds the budget\n"
            "     c) Do NOT include it in product_recommendations array\n"
            "     Example: 'Unfortunately, I don't have any laptops under $1,400. The closest option is the [name] at $1,999, which is $599 over your budget.'\n\n"
            "DECISION LOGIC:\n"
            "1. If the user's request is VAGUE or missing key details (use case, budget, performance needs):\n"
            "   - Ask 1-2 specific follow-up questions to clarify\n"
            "   - Do NOT recommend products yet\n"
            "   - Keep your response to 2-3 sentences\n\n"
            "2. If you have ENOUGH information to make a confident recommendation:\n"
            "   - First, filter products by budget if specified\n"
            "   - Recommend EXACTLY 2 products:\n"
            "     a) PRIMARY: The best overall match for their needs (highest confidence)\n"
            "     b) ALTERNATIVE: A smart alternative with different trade-offs\n"
            "        - Should differ in price, specs, or use case focus\n"
            "        - NOT just the second-highest similarity score\n"
            "        - Consider: budget-friendly option, performance upgrade, different vendor, etc.\n"
            "   - Give a brief 2-3 sentence explanation highlighting both options\n"
            "   - Focus on how each matches their specific needs differently\n\n"
            "STYLE GUIDELINES:\n"
            "- Be conversational and concise (max 3-4 sentences)\n"
            "- Highlight the key difference between primary and alternative\n"
            "- Match the user's tone (casual vs technical)\n"
            "- Only recommend from the provided product context\n\n"
            "OUTPUT FORMAT (valid JSON):\n"
            "{\n"
            '  "reply": "<2-4 sentence response mentioning both options>",\n'
            '  "reasoning": "<brief internal reasoning>",\n'
            '  "product_recommendations": [<exactly 2 products if recommending, or empty [] if asking questions OR if no products match budget>]\n'
            "}\n\n"
            "Product recommendation structure:\n"
            '{"sku": "...", "name": "...", "rationale": "<1 sentence why this fits>", "confidence": 0.0-1.0}\n'
            "IMPORTANT: First product = PRIMARY recommendation (highest confidence), Second product = ALTERNATIVE option"
        )

    def _format_product_context(self, products: Sequence[RetrievedProduct]) -> str:
        """Format product context with specs and optionally matched keywords/explanation."""
        lines: List[str] = []
        for product in products:
            # Basic product specs
            product_line = (
                f"- SKU {product.sku}: {product.name}; CPU: {product.cpu}; GPU: {product.gpu}; "
                f"RAM: {product.ram}; Storage: {product.storage}; Price: ${product.price}"
            )

            # Add matched keywords if available (from hybrid search)
            if product.matched_keywords:
                product_line += f"; Matched terms: {', '.join(product.matched_keywords[:5])}"

            # Add knowledge base information if available
            if product.knowledge:
                kb = product.knowledge
                # Add summary (truncate to 150 chars for context)
                if kb.summary:
                    product_line += f"\n  Summary: {kb.summary[:150]}..."
                # Add key strengths (top 3)
                if kb.strengths:
                    product_line += f"\n  Strengths: {'; '.join(kb.strengths[:3])}"
                # Add weaknesses (top 2)
                if kb.weaknesses:
                    product_line += f"\n  Weaknesses: {'; '.join(kb.weaknesses[:2])}"
                # Add use cases (top 3)
                if kb.use_cases:
                    product_line += f"\n  Best for: {'; '.join(kb.use_cases[:3])}"

            # Add additional context/explanation if available (may include knowledge base info)
            if product.explanation:
                product_line += f"\n  Additional context: {product.explanation[:200]}"

            lines.append(product_line)
        return "\n".join(lines)

    @staticmethod
    def _product_name_for_sku(products: Sequence[RetrievedProduct], sku: str) -> Optional[str]:
        for product in products:
            if product.sku == sku:
                return product.name
        return None

    # ------------------------------------------------------------------ offline
    def _offline_response(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        reply_lines = ["(Offline mode)"]
        if context_products:
            best = context_products[0]
            reply_lines.append(
                f"I recommend **{best.name}** because it closely matches your requirements ({best.cpu}, {best.gpu}, {best.ram})."
            )
            if len(context_products) > 1:
                reply_lines.append("You may also want to consider these alternatives:")
                for product in context_products[1:3]:
                    reply_lines.append(f"- {product.name} ({product.cpu}, {product.gpu})")
        else:
            reply_lines.append("I could not find relevant products yet. Could you share more about your needs?")

        recommendations = [
            LLMProductRecommendation(
                sku=product.sku,
                name=product.name,
                rationale=product.explanation or "High semantic similarity to the query.",
            )
            for product in context_products[:3]
        ]

        return LLMResult(
            reply="\n".join(reply_lines),
            reasoning="Generated via offline fallback heuristics.",
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------ helpers
    def _initialise_model(self, model_name: str, use_json_mode: bool = True) -> Optional[genai.GenerativeModel]:
        try:
            self._model_name = model_name
            return self._build_model(model_name, use_json_mode=use_json_mode)
        except ValueError as exc:
            logger.error("Model initialization failed for '%s': %s", model_name, exc, exc_info=True)
            if "Invalid model name" in str(exc):
                alternate = self._alternate_model_name(model_name)
                if alternate and alternate != model_name:
                    logger.info("Retrying Gemini initialisation with '%s'.", alternate)
                    self._model_name = alternate
                    return self._build_model(alternate, use_json_mode=use_json_mode)
            if model_name != self._fallback_model_name:
                logger.info("Falling back to Gemini model '%s'.", self._fallback_model_name)
                self._model_name = self._fallback_model_name
                return self._build_model(self._fallback_model_name, use_json_mode=use_json_mode)
            raise

    def _build_model(self, model_name: str, use_json_mode: bool = True) -> genai.GenerativeModel:
        import google.generativeai.types as genai_types

        # Set safety settings to be less restrictive
        safety_settings = {
            genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai_types.HarmBlockThreshold.BLOCK_NONE,
            genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai_types.HarmBlockThreshold.BLOCK_NONE,
            genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai_types.HarmBlockThreshold.BLOCK_NONE,
            genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai_types.HarmBlockThreshold.BLOCK_NONE,
        }

        generation_config = {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 20,
            "max_output_tokens": 2048,
        }

        # Only use JSON mode for non-streaming to avoid raw JSON in UI
        if use_json_mode:
            generation_config["response_mime_type"] = "application/json"

        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._system_prompt() if use_json_mode else self._streaming_system_prompt(),
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

    @staticmethod
    def _alternate_model_name(model_name: str) -> Optional[str]:
        if model_name.startswith(("models/", "tunedModels/")):
            return model_name.split("/", 1)[-1]
        return f"models/{model_name}"

    def _extract_text(self, response: Any) -> str:
        try:
            return response.text
        except ValueError:
            pass

        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", []) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    return text
        return ""

    def _heuristic_parse(
        self, raw_text: str, context_products: Sequence[RetrievedProduct]
    ) -> Optional[LLMResult]:
        reply_match = re.search(r'"reply"\s*:\s*"(?P<reply>.*?)"', raw_text, re.DOTALL)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"(?P<reasoning>.*?)"', raw_text, re.DOTALL)
        items = []
        for match in re.finditer(
            r'"sku"\s*:\s*"(?P<sku>[^"]+)"[^}]*?"name"\s*:\s*"(?P<name>[^"]+)"[^}]*?"rationale"\s*:\s*"(?P<rationale>.*?)"',
            raw_text,
            re.DOTALL,
        ):
            sku = match.group("sku").strip()
            name = match.group("name").strip()
            rationale = match.group("rationale").strip()
            if sku:
                items.append((sku, name, rationale))

        if not reply_match and not items:
            return None

        reply = self._clean_json_string(reply_match.group("reply")) if reply_match else ""
        reasoning = (
            self._clean_json_string(reasoning_match.group("reasoning")) if reasoning_match else None
        )

        recommendations = []
        for sku, name, rationale in items:
            recommendations.append(
                LLMProductRecommendation(
                    sku=sku,
                    name=name or self._product_name_for_sku(context_products, sku) or sku,
                    rationale=self._clean_json_string(rationale),
                    confidence=None,
                )
            )

        return LLMResult(reply=reply, reasoning=reasoning, recommendations=recommendations)

    @staticmethod
    def _clean_json_string(value: str) -> str:
        return value.replace("\\n", "\n").replace("\\\"", '"').strip()
