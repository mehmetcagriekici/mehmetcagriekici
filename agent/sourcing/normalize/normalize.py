from sourcing.constants.constants import REQUIRED_FIELDS
from sourcing.custom_types.posting import Posting, Skip, SkipReason


def normalize(posts: list[Posting]) -> tuple[list[Posting], list[Skip]]:
    normalized_posts: list[Posting] = []
    skips: list[Skip] = []

    for post in posts:
        empties = [key for key in REQUIRED_FIELDS if post[key] is None]
        if empties:
            skips.append(Skip(what='skip', reason=SkipReason.MISSING_FIELD, detail='missing field'))
        else:
            normalized_posts.append(post)

    return normalized_posts, skips
