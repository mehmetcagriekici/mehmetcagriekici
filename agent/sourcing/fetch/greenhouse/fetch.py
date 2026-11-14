import httpx

from sourcing.constants.urls import greenhouse_jobs
from sourcing.custom_types.posting import GreenhousePosting, Skip, SkipReason


async def fetch(board: str) -> list[GreenhousePosting] | Skip:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(greenhouse_jobs(board))
            r.raise_for_status()
            body = r.json()
            if not isinstance(body, dict) or not isinstance(body.get('jobs'), list):
                return Skip(what=board, reason=SkipReason.FETCH_FAILED, detail="no job list")
            return body['jobs']
        except httpx.HTTPError:
            return Skip(what=board, reason=SkipReason.FETCH_FAILED, detail="http error")
        except ValueError:
            return Skip(what=board, reason=SkipReason.FETCH_FAILED, detail="invalid json")
