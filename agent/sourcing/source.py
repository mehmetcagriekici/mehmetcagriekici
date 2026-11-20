import asyncio
import json
from pathlib import Path

from sourcing.constants.constants import WAIT_TIME
from sourcing.custom_types.posting import Posting, Skip
from sourcing.fetch.greenhouse.fetch import fetch as greenhouse_fetch
from sourcing.fetch.greenhouse.reshape import reshape as greenhouse_reshape
from sourcing.normalize.normalize import normalize

adapters = {
        'greenhouse': {
            'fetch': greenhouse_fetch,
            'reshape': greenhouse_reshape,
            }
        }


async def source(ats: str) -> tuple[list[Posting], list[Skip]]:
    COMPANIES = Path(__file__).parent / "companies.json"
    with open(COMPANIES) as f:
        companies = json.load(f)
    skips: list[Skip] = []
    posts: list[Posting] = []
    if ats not in adapters:
        raise ValueError(f"{ats} not found")
    boards = [c['board'] for c in companies if c['ats'] == ats and c['enabled']]
    fetch_fn = adapters[ats]['fetch']
    for b in boards:
        res = await fetch_fn(b)
        # check if skip
        if not isinstance(res, list):
            skips.append(res)
            continue
        # results is the jobs list - reshape after fetch
        reshape = adapters[ats]['reshape']
        reshaped_posts = reshape(b, res)
        normalized_posts, normalized_skips = normalize(reshaped_posts)
        # add skips to normalized skips
        skips += normalized_skips
        posts += normalized_posts
        # breaktime before the next board - to prevent ats 429
        await asyncio.sleep(WAIT_TIME)
    return posts, skips
