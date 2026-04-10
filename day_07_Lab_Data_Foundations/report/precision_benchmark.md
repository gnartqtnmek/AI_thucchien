# Precision@k Benchmark

- k: **3**
- Number of benchmark queries: **5**

| Strategy | Avg Precision@3 | Hit Rate | Total Chunks | Q1 | Q2 | Q3 | Q4 | Q5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| recursive | 0.533 | 0.800 | 106 | 0.667 | 0.000 | 1.000 | 0.333 | 0.667 |
| fixed_size | 0.533 | 0.800 | 108 | 1.000 | 0.000 | 1.000 | 0.333 | 0.333 |
| sentence | 0.400 | 0.800 | 120 | 0.333 | 0.000 | 1.000 | 0.333 | 0.333 |

**Best strategy:** recursive (Avg Precision@3 = 0.533, Source Coverage = 0.800, Hit Rate = 0.800)