# Which cohort did we measure?

The researcher asks for the mean endpoint for the cohort named in a protocol. A demo dataset accompanies the real datasets so students can practice. Repair `estimate(protocol, datasets)` in `analysis.py`. Use Python's standard library.

The protocol gives two strings, `cohort` and `endpoint`. The datasets dictionary maps cohort names to lists of record dictionaries. Use the exact requested cohort and endpoint. The record values for that endpoint are finite numbers or None. Ignore None. An absent endpoint in any record means the supplied data do not support the requested result.

Return a dictionary with `cohort` (the requested name), `status`, `mean`, and `n` (number used). On success the status is `ok`. When the cohort is absent, use `missing cohort`. For an absent endpoint use `missing endpoint`. For an empty cohort or all missing readings use `no observations`. For these three outcomes return None for the mean and zero for n. Demo data are usable only when explicitly requested. Explain your repair and check it on a small example.
