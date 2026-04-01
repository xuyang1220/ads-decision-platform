class AdsPlatformError(Exception):
    """Base exception for platform-specific failures."""


class MissingBudgetStateError(AdsPlatformError):
    """Raised when budget state is unavailable for an entity."""


class InvalidAuctionInputError(AdsPlatformError):
    """Raised when the auction input is invalid."""
