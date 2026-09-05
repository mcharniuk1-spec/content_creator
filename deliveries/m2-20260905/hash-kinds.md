# Digest conventions

The original demo receipt stores SHA-256 of a canonical JSON object. Each ScriptCard source map stores SHA-256 of the exact source file bytes. Both were independently recomputed; they are different digest kinds and must not be compared directly. Original artifacts remain unchanged. Stage receipts use exact file-byte hashes and bind their parent receipts. A release binds implementation, configuration and corpus identities. A code change can therefore yield a new release ID while all underlying observations and numeric results remain identical.
