from typing import AsyncIterator, Protocol, runtime_checkable

from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = (
    "Sen sabırlı, deneyimli bir yazılım eğitmenisin. "
    "Karmaşık konuları gündelik benzetmelerle anlatırsın.\n\n"
    "Cevabının uzunluğunu ve biçimini soruya göre ayarla. "
    "Selamlaşma, sohbet veya basit sorulara KISA ve doğal cevap ver — başlık, liste, "
    "kod bloğu kullanma, sadece birkaç cümle yeter. "
    "Yalnızca konu gerçekten teknik veya çok parçalıysa Markdown biçimlendirme "
    "(başlık, kod bloğu, kalın vurgu) ve adım adım açıklama kullan.\n\n"
    "Kullanıcı kod gönderirse önce ne yaptığını açıkla, sonra varsa hatayı göster, "
    "en son iyileştirme öner.\n\n"
    "Emin olmadığın bilgilerde tahmin yürütme; 'bundan emin değilim' de. "
    "Kütüphane, fonksiyon veya sürüm adı uydurma. "
    "Uydurma bir cevap vermektense 'bilmiyorum' demek daha iyidir."
)


@runtime_checkable
class LLMProvider(Protocol):
    async def stream(
        self,
        message: str,
        history: list[types.Content],
    ) -> AsyncIterator[str]: ...


class GeminiProvider:
    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=3000,
        )

    async def stream(
        self,
        message: str,
        history: list[types.Content],
    ) -> AsyncIterator[str]:
        contents = history + [
            types.Content(role="user", parts=[types.Part(text=message)])
        ]
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=self._config,
        ):
            if chunk.text:
                yield chunk.text
