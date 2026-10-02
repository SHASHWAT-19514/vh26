# Detection decisions

The configured 15-minute dispersal window is inclusive. Layers are positional by hop: hop 1 is L1, hop 2 is L2, and hop 3+ is L3, with a terminal behavior override. Because the source dataset has no balances, residuals are always labelled estimated and are calculated from traced inflows less traced outflows. Timestamps are naive IST. All thresholds live in `config/detection.yaml` and are hashed into evidence metadata.
