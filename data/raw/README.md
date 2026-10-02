# Raw source cache

Retrieved blobs are stored by source ID and upstream path. They are immutable
and excluded from Git for size. `sources/lock.json` records pinned URLs, paths,
versions, sizes, dates, and SHA-256 checksums for reproducible retrieval.
