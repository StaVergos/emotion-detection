from typing import List
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.api.schemas import Error


class APIError(HTTPException):
    def __init__(self, errors: List[Error], status_code: int = HTTP_400_BAD_REQUEST):
        # we pass detail=None because our handler will ignore it
        super().__init__(status_code=status_code, detail=None)
        self.errors = errors
