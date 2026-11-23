# Recorded conversations (regression fixtures)

Each `.txt` file here is a complete interview with the voice agent, stored as plain text and replayed by
`tests/conversations/test_conversations.py` (`make conversation-test`). The replay feeds the recorded `user:` lines to
the agent in keyword mode, with no OpenAI call, and fails if the agent's side of the conversation or any expectation
changes. The conversations are in Turkish because the app speaks Turkish.

## Files

| File | What it guards |
| --- | --- |
| `01_pack_year_side_question.txt` | A side question in the middle of a confirmation ("what does 5 pack-years mean?") is answered and the same question is asked again; "what does this mean?" and "why do you ask?" on later questions. |
| `02_woman_35_all_symptoms.txt` | Woman of 35 with every risk factor except COPD and all seven symptoms: the 6-year layer stays below the screening threshold, the relative-risk, natural-frequency and projection sentences are spoken, and prompt assessment is advised through the symptom layer although the NICE age rule does not apply. |
| `03_phone_male_45_short_answers.txt` | First phone trial: terse answers such as "45 yaş erkek" are understood at once and the confirmation repeats the dose in the user's own words instead of pack-years. |
| `04_phone_voice_twenty_packs.txt` | Second phone trial: a speech-to-text error ("twenty packs a day") is questioned, the correction is confirmed, and the four symptoms the user did not mention are asked one by one. |

## Format

| Line | Meaning |
| --- | --- |
| `agent: …` / `user: …` | One turn of the interview. |
| `# …` | Comment: header (session, model, input mode, channel), the result block written at the end, free notes. |
| `>> …` | A note attached to the turn above it, typically the bug that the recording documents. |
| `# beklenen: KEY=VALUE` | An expectation ("beklenen" = expected) checked after the replay. |

Expectation keys: any evidence variable (`COUGHING=1`, `_pack_years=5`, `FAMILY_HISTORY=yok` for "not recorded"), any
field of the result (`risk_level_factors="low"`), and `ajan_der="…"` (the agent says), `ajan_demez="…"` (the agent
never says), `belirti=` (symptom layer level), `acil=` (prompt assessment advised), `alarm=` (NICE NG12 rule),
`bitti=` (interview finished).

## Adding a case

Download the transcript from the result screen of the app ("Konuşma kaydını indir"), copy it here under an English
name, add `>>` notes where something went wrong and `# beklenen:` lines for what should happen, and run
`python tools/replay_conversation.py <file>`. Transcripts of real sessions are health data: `data/conversations/` is
git-ignored, and only invented cases belong in this folder. `make_fixtures.py` regenerates the four files after an
intended change to the agent's wording.
