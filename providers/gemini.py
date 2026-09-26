from collections.abc import AsyncIterator, Sequence
from typing import Any

from google.genai import types
from google.genai.errors import ClientError, ServerError

from providers.base import ChatMessage
from providers.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)


class GeminiProvider:
    def __init__(
        self,
        client: Any,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

        self._generate_config = types.GenerateContentConfig(
            system_instruction=(
                "Sen deneyimli bir yazılım eğitmenisin. "
                "Doğru ve anlaşılır cevap ver. "
                "Basit sorulara kısa cevap ver. "
                "Detay istenmedikçe gereksiz açıklama yapma. "
                "Emin olmadığın bilgiyi uydurma."
            ),
            temperature=0.2,
            max_output_tokens=200,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

    async def stream(
        self,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[str]:
        contents = [
            types.Content(
                role=message.role,
                parts=[types.Part(text=message.content)],
            )
            for message in messages
        ]

        try:
            stream = await self._client.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=self._generate_config,
            )

            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except ServerError as error:
            if error.code == 503:
                raise ProviderUnavailableError from error

            raise ProviderError from error

        except ClientError as error:
            if error.code == 429:
                raise ProviderRateLimitError from error

            raise ProviderRequestError from error
