from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from sourcing.constants.constants import REQUIRED_FIELDS
from sourcing.custom_types.posting import Posting, Skip, SkipReason


def normalize(posts: list[Posting]) -> tuple[list[Posting], list[Skip]]:
    normalized_posts: list[Posting] = []
    skips: list[Skip] = []

    for post in posts:
        # missing key - key does not exist
        missing = Posting.__required_keys__ - post.keys()
        if missing:
            detail = " ".join(missing)
            skips.append(Skip(
                what=f"skipping post {post.get('id')}",
                reason=SkipReason.MISSING_KEY,
                detail=f"missing keys: {detail}",
                ))
            continue

        empties = [key for key in REQUIRED_FIELDS if post.get(key) is None]
        if empties:
            detail = " ".join(empties)
            # value is none
            skips.append(Skip(what=f"skipping post {post.get('id')}",
                              reason=SkipReason.MISSING_FIELD,
                              detail=f"missing fields: {detail}",
                              ))
        else:
            # check for stale (more than 30 days old)
            if post['posted_at'] is not None:
                # check if posted_at has a timezone
                if post['posted_at'].tzinfo is None:
                    skips.append(Skip(what=f"skipping post {post.get('id')}",
                                      reason=SkipReason.MISSING_FIELD,
                                      detail="posted at does not have a timezone",
                                      ))
                    continue
                if datetime.now(timezone.utc) - timedelta(days=30) > post['posted_at']:
                    skips.append(Skip(what=f"skipping post {post.get('id')}",
                                      reason=SkipReason.STALE,
                                      detail="post is more than 30 days old",
                                      ))
                    continue
            # normalize html description
            # or " " -> only for typecheck, code never reaches it, it's covered above
            soup = BeautifulSoup(post.get('description') or " ", 'html.parser')
            post['description'] = soup.get_text("\n", strip=True)
            normalized_posts.append(post)

    return normalized_posts, skips
