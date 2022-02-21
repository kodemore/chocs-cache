class CacheError(Exception):
    @staticmethod
    def for_not_found(item_id: str) -> "CacheError":
        return CacheError(f"Could not retrieve cache item with given id `{item_id}`")
