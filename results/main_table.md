# Results

**n = 40** hand-labelled examples (37 with a decision label). Simple baseline scored on out-of-fold cross-validated predictions.

All intervals are percentile bootstrap 95% CIs over 2000 resamples. At this sample size the intervals, not the point estimates, are the result -- see the README's *What is misleading about my headline number* section.

Classes with zero gold examples (billing_or_purchase, how_to) are **unmeasured** and excluded from macro-F1.


## Intent -- all 40

| system   |   n |   accuracy | acc_95CI     |   macro_f1 | f1_95CI      |   classes_measured |
|:---------|----:|-----------:|:-------------|-----------:|:-------------|-------------------:|
| agent    |  40 |      0.625 | [0.47, 0.78] |      0.555 | [0.35, 0.68] |                  5 |
| simple   |  40 |      0.5   | [0.35, 0.65] |      0.236 | [0.12, 0.35] |                  5 |
| trivial  |  40 |      0.475 | [0.33, 0.62] |      0.129 | [0.10, 0.15] |                  5 |


## Intent -- natural slice (deployment estimate, n=24)

| system   |   n |   accuracy | acc_95CI     |   macro_f1 | f1_95CI      |   classes_measured |
|:---------|----:|-----------:|:-------------|-----------:|:-------------|-------------------:|
| agent    |  24 |      0.708 | [0.54, 0.88] |      0.583 | [0.32, 0.72] |                  4 |
| trivial  |  24 |      0.667 | [0.46, 0.83] |      0.2   | [0.16, 0.23] |                  4 |
| simple   |  24 |      0.625 | [0.42, 0.83] |      0.197 | [0.16, 0.23] |                  4 |


## Intent -- targeted slice (diagnostic only, n=16)

| system   |   n |   accuracy | acc_95CI     |   macro_f1 | f1_95CI      |   classes_measured |
|:---------|----:|-----------:|:-------------|-----------:|:-------------|-------------------:|
| agent    |  16 |      0.5   | [0.25, 0.75] |      0.476 | [0.20, 0.66] |                  5 |
| simple   |  16 |      0.312 | [0.06, 0.56] |      0.275 | [0.05, 0.43] |                  5 |
| trivial  |  16 |      0.188 | [0.00, 0.38] |      0.063 | [0.00, 0.11] |                  5 |


## Escalation -- all

| system   |   escalate_precision |   escalate_recall | recall_95CI   |   escalate_f1 |   missed_escalations |   n_gold_escalate |   reason_code_acc |
|:---------|---------------------:|------------------:|:--------------|--------------:|---------------------:|------------------:|------------------:|
| agent    |                0.625 |             0.909 | [0.73, 1.00]  |         0.741 |                    1 |                11 |             0.27  |
| simple   |                0     |             0     | [0.00, 0.00]  |         0     |                   11 |                11 |             0     |
| trivial  |                0     |             0     | [0.00, 0.00]  |         0     |                   11 |                11 |             0.135 |


## Reply quality

| system   |   n_judged |   groundedness |   action |   tone |   judge_mean |   safety_violations |   fabricated_url_% |
|:---------|-----------:|---------------:|---------:|-------:|-------------:|--------------------:|-------------------:|
| agent    |         20 |           2.95 |     3    |   3    |         2.98 |                   0 |                  0 |
| trivial  |         20 |           2.95 |     2.95 |   2.95 |         2.95 |                   0 |                  0 |
| simple   |         20 |           2.65 |     2.5  |   2.7  |         2.62 |                   0 |                  0 |


## Agent confusion matrix (rows = gold)

|                       |   software_bug |   how_to |   account_access |   hardware_or_repair |   billing_or_purchase |   feedback_or_complaint |   other |
|:----------------------|---------------:|---------:|-----------------:|---------------------:|----------------------:|------------------------:|--------:|
| software_bug          |             16 |        1 |                0 |                    2 |                     0 |                       0 |       0 |
| how_to                |              0 |        0 |                0 |                    0 |                     0 |                       0 |       0 |
| account_access        |              1 |        1 |                4 |                    0 |                     1 |                       0 |       0 |
| hardware_or_repair    |              1 |        0 |                0 |                    3 |                     0 |                       1 |       0 |
| billing_or_purchase   |              0 |        0 |                0 |                    0 |                     0 |                       0 |       0 |
| feedback_or_complaint |              2 |        3 |                0 |                    0 |                     0 |                       0 |       0 |
| other                 |              2 |        0 |                0 |                    0 |                     0 |                       0 |       2 |


## Agent per-class intent report

```
                       precision    recall  f1-score   support

       account_access       1.00      0.57      0.73         7
  billing_or_purchase       0.00      0.00      0.00         0
feedback_or_complaint       0.00      0.00      0.00         5
   hardware_or_repair       0.60      0.60      0.60         5
               how_to       0.00      0.00      0.00         0
                other       1.00      0.50      0.67         4
         software_bug       0.73      0.84      0.78        19

             accuracy                           0.62        40
            macro avg       0.48      0.36      0.40        40
         weighted avg       0.70      0.62      0.64        40

```