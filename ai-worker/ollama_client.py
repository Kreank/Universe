"""Async-Client fuer die lokale Ollama-HTTP-API.

Robustheit (ADR-003): Ist Ollama nicht erreichbar oder liefert es Unsinn, wird
`OllamaUnavailable` geworfen. Der Worker faengt das ab, stellt den Job zurueck
und crasht NICHT. KI ist Veredelung, kein kritischer Pfad.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from config import settings

log = logging.getLogger("ollama")


class OllamaUnavailable(RuntimeError):
    """Transienter Fehler: Ollama nicht erreichbar / unbrauchbare Antwort.

    Aufrufer behandeln das als 'spaeter erneut versuchen' (Job zurueckstellen).
    """


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> None:
        self._base = (base_url or settings.ollama_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._embed_model = embed_model or settings.ollama_embed_model
        # Grosszuegiges Default-Timeout; einzelne Calls setzen ihr eigenes.
        self._client = httpx.AsyncClient(
            base_url=self._base,
            timeout=httpx.Timeout(settings.generate_timeout_seconds),
        )
        self._dim_warned = False

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------ generate
    async def generate(self, system: str, prompt: str) -> str:
        """Einen Text via POST /api/generate (stream=false) erzeugen."""
        payload: dict[str, Any] = {
            "model": self._model,
            "system": system,
            "prompt": prompt,
            "stream": False,
        }
        try:
            resp = await self._client.post(
                "/api/generate", json=payload, timeout=settings.generate_timeout_seconds
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:  # ValueError = JSON-Decode
            raise OllamaUnavailable(f"generate fehlgeschlagen: {exc}") from exc

        text = (data or {}).get("response", "")
        if not isinstance(text, str) or not text.strip():
            raise OllamaUnavailable("generate lieferte eine leere Antwort")
        return text.strip()

    # --------------------------------------------------------------------- embed
    async def embed(self, text: str) -> list[float]:
        """Einen Embedding-Vektor via POST /api/embed erzeugen.

        Dimension wird auf settings.embed_dim (768, passend zu vector(768))
        normalisiert. nomic-embed-text liefert nativ 768. Liefert ein anderes
        Modell eine abweichende Dimension, wird per Trunc/Pad angeglichen, damit
        der INSERT in pgvector nicht hart scheitert (Qualitaet leidet -> Modell
        pruefen).
        """
        payload = {"model": self._embed_model, "input": text}
        try:
            resp = await self._client.post(
                "/api/embed", json=payload, timeout=settings.embed_timeout_seconds
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailable(f"embed fehlgeschlagen: {exc}") from exc

        vec = self._extract_embedding(data)
        return self._normalize_dim(vec)

    # ------------------------------------------------------------------ intern
    @staticmethod
    def _extract_embedding(data: Any) -> list[float]:
        if not isinstance(data, dict):
            raise OllamaUnavailable("embed: unerwartete Antwortstruktur")
        # /api/embed -> {"embeddings": [[...]]}; aelteres /api/embeddings -> {"embedding": [...]}
        if isinstance(data.get("embeddings"), list) and data["embeddings"]:
            vec = data["embeddings"][0]
        elif isinstance(data.get("embedding"), list):
            vec = data["embedding"]
        else:
            raise OllamaUnavailable("embed: kein Embedding in der Antwort")
        if not isinstance(vec, list) or not vec:
            raise OllamaUnavailable("embed: leerer Embedding-Vektor")
        try:
            return [float(x) for x in vec]
        except (TypeError, ValueError) as exc:
            raise OllamaUnavailable(f"embed: nicht-numerischer Vektor ({exc})") from exc

    def _normalize_dim(self, vec: list[float]) -> list[float]:
        dim = settings.embed_dim
        if len(vec) == dim:
            return vec
        if not self._dim_warned:
            log.warning(
                "Embedding-Dimension %d != erwartet %d -> Trunc/Pad. Modell '%s' pruefen.",
                len(vec), dim, self._embed_model,
            )
            self._dim_warned = True
        if len(vec) > dim:
            return vec[:dim]
        return vec + [0.0] * (dim - len(vec))
