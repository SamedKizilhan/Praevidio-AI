# Documentation

Start with the project [`README`](../README.md). The documents here go deeper.

## The system

| Document | Content |
| --- | --- |
| [`architecture.md`](architecture.md) | Components, what happens in one conversation turn, API endpoints, data and privacy, design choices |
| [`dictionary.md`](dictionary.md) | Glossary of clinical, modelling and engineering terms |
| [`ProjectPlan_Fall2026.md`](ProjectPlan_Fall2026.md) | Plan and status of the fall term |

## The risk model

Read in this order to follow how the model developed.

| Document | Content | Kind |
| --- | --- | --- |
| [`model_parameters.md`](model_parameters.md) | Reference: structure, every parameter with its source, the effect of each answer | written |
| [`model_v3_design.md`](model_v3_design.md) | Four findings of the review of the spring model and the design of v3.0 | written, English and Turkish |
| [`model_v3_1_calibration_fix.md`](model_v3_1_calibration_fix.md) | The fifth finding: root causes, fixes, tests and the change for each of 43 profiles | narrative written, table generated (`make v31-diff`) |
| [`symptom_layer.md`](symptom_layer.md) | Why the screening and the referral question got separate layers; how a small percentage is explained | written, English and Turkish |
| [`model_comparison_v2_v3.md`](model_comparison_v2_v3.md) | 33 cases scored by v2, v3.0 and v3.1 side by side | generated (`make compare`) |
| [`sensitivity_v3.md`](sensitivity_v3.md) | Eight cases under nine parameter settings | generated (`make sensitivity`) |
| [`nhanes_symptom_baselines.md`](nhanes_symptom_baselines.md) | Symptom frequencies in people without cancer, NHANES against the model | generated (`make nhanes`) |

## Validation material

| Location | Content |
| --- | --- |
| [`../tests/expert_validation/`](../tests/expert_validation/) | Ten cases, the form for the chest physician (Turkish), the model answer key and the analysis script |
| [`../tests/usability/`](../tests/usability/) | Usability protocol, SUS-TR questionnaire (Turkish) and scoring |
| [`../tests/conversations/`](../tests/conversations/) | Recorded conversations replayed as regression tests |
| [`../tests/model/`](../tests/model/) | Regression baseline and plausibility tests of the model |

## History

[`history/`](history/) holds the documents of the spring model (v2). They are accurate for that model and are kept
to show how the project developed; each begins with a note saying what replaced it.

| Document | Content |
| --- | --- |
| [`history/v2_symptom_cpt_derivation.md`](history/v2_symptom_cpt_derivation.md) | Derivation of the v2 symptom tables from the literature |
| [`history/v2_explaining_away_calibration.md`](history/v2_explaining_away_calibration.md) | The explaining-away problem in v2 and its calibration fix |
| [`history/v2_new_factor_calibration.md`](history/v2_new_factor_calibration.md) | Check of the odds ratios for family history, occupational exposure and air pollution in v2 (Turkish) |
| [`history/v2_explainability_notes.md`](history/v2_explainability_notes.md) | Shapley contributions for a sample case under v2 (Turkish) |
| [`history/v2_scenario_report.md`](history/v2_scenario_report.md) | The 21 test scenarios under v2 (Turkish) |
| [`history/v2_architecture_flow.png`](history/v2_architecture_flow.png) | Flow diagram of the spring terminal agent |

## Conventions

File names and documents are in English. A design note first written in Turkish keeps the Turkish text below the
English one. Generated reports are in English only and say at the top which command produces them; change the
generating script, not the file. Material read by Turkish speakers (the expert form, the usability questionnaire,
recorded conversations) stays in Turkish with an English note at the top.
