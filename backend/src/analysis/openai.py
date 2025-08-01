from fastapi import HTTPException, status
from openai import OpenAI, OpenAIError
from src.api.config import OPENAI_API_KEY, get_logger

logger = get_logger()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in the environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)


def make_request_to_openai(prompt: dict):
    logger.info(f"Making request to OpenAI with prompt: {prompt}")
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=prompt,
        )
        logger.info(f"OpenAI response: {resp}")

    except OpenAIError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.get("error", {}).get(
                "message", "An error occurred while processing your request."
            ),
            type=e.get("error", {}).get("type", "unknown_error"),
        )
    return resp.choices[0].message.content
