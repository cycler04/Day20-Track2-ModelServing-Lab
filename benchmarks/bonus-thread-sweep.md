# Bonus — Thread sweep

Model: `qwen2.5-1.5b-instruct-q4_k_m.gguf`  ·  GPU layers: `99`

| threads | tg64 (tok/s) |
|---:|---:|
| 1 | 11.2 |
| 2 | 15.6 |
| 4 | 20.4 |
| 8 | 21.1 |
| 16 | 15.1 |

**Best**: `-t 8` at 21.1 tok/s.

Look at the curve. If it peaks around your **physical** core count and drops as you go higher, that's the memory-bandwidth ceiling: extra threads fight over the same memory channels and slow each other down.
