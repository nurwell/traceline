# Incident Timeline

| ID | Time UTC | Source | Level | Event |
|---|---|---|---|---|
| 57ca2a41f32a6e21 | 2026-05-13 14:02:11 | deploy | unknown | deploy started version=8f31a2 |
| bcaf498af94e8542 | 2026-05-13 14:03:02 | app | error | ERROR checkout-api payment timeout request_id=req_91 |
| 38e93363327f28af | 2026-05-13 14:03:04 | nginx | error | "POST /checkout" 504 upstream timed out |
| 59c3062b4ac746f6 | 2026-05-13 14:03:07 | app | error | ERROR checkout-api database pool exhausted request_id=req_92 |
| dae42283c02f5ca1 | 2026-05-13 14:03:09 | nginx | error | "POST /checkout" 502 bad gateway |
| 869d7be12cb93623 | 2026-05-13 14:04:30 | deploy | unknown | rollback started version=7c21be |
| 4810e542843072a9 | 2026-05-13 14:05:10 | app | info | INFO checkout-api recovered |
