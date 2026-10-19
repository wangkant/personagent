# Eval results, 2026-10-18

**English** · [简体中文](README.zh-CN.md)

`personagent eval` drives the real agent through labelled chat moments and keeps every case, reply and verdict. This run used personagent 1.2.2 plus the changes listed under Unreleased in the [changelog](../../../CHANGELOG.md), with the shipped example character (Nova in English, 小夏 in Chinese) on two models through OpenRouter: `deepseek/deepseek-v4.1-flash` and `openai/gpt-6-luna`. Every case ran three times, each in a fresh deployment.

Brackets are 95% intervals. They count each case once, so the three tries add no sample size. How each suite works is in the [user guide](../../guide.md#measure-it).

## When it speaks

There are 60 group-chat moments per language: 20 where nobody names it, 20 right after it spoke, and 20 where its name appears. Half of each kind are labelled quiet. No judge is involved: each try is either right or wrong against its label.

| Tries right | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| English | 83% [72–91] | 93% [84–97] |
| Chinese | 80% [68–88] | 91% [80–96] |

- It rarely ignores a message meant for it: at most 3 of 90 such tries, per model and language.
- When nobody named it, or it had just spoken, it got 93–100% of tries right.
- Most misses are its name used for something else, or said about it to someone else: a cinema, an earbud brand, a puppy, a quote. On those 10 moments per language, deepseek answered anyway in 25 of 30 English tries and 29 of 30 Chinese ones. gpt-6-luna answered in 12 and 16. personagent treats a name as a call, and the model seldom overrides that.
- For reference, a bot that answers exactly when it is named gets 50% of these moments right.

## Playing the character

personagent is compared with the same model given only the character text as its system prompt, which is what you get by pasting the character into a chat model. There are 40 moments per language, 22 in a group and 18 in DMs. Claude Opus 5.5 judged each pair blind twice, in separate sessions, with the replies swapped. A reply wins only when both picks agree, and a split counts as half. Saying nothing when called counts as a loss.

| personagent's win rate | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| English | 63% [47–76] | 75% [59–86] |
| Chinese | 58% [43–72] | 53% [38–67] |

- In English it beats the plain prompt on both models. In Chinese the edge is within the noise.
- The judge matters. A second judge, Claude Haiku 5.5 run through `personagent eval`, reached the same outcome on only 53–64% of the pairs. Its win rates were within 4 points of Opus's except on gpt-6-luna in English, where it gave 62%.
- Moments vary from try to try: on deepseek in English, 11 of 40 moments won all three tries, 9 never won, and 20 went both ways.

## Learning from corrections

There are 20 scenarios per language, run through the real reaction path:

- 7 teach a group convention the model can't guess, such as "we call the gym the cave" or "the BBQ is at Jules's this year".
- 6 teach a style.
- 7 must be held: a bystander's correction, a troll's, and one the person walks away from.

A later, differently worded message in the same chat checks whether the character uses what it was taught. It runs once before the correction and once after, and Opus 5.5 judged the replies.

The first run on this date showed that a promoted correction almost never carried over. What got promoted was the character's own retry, as an example of better wording, and the next message on the same subject came out without the fact. Corrections now also keep their lesson as one sentence, such as "This group calls the gym 'the cave'.", and every later prompt in that chat carries it (see the [user guide](../../guide.md#corrections)). The learning suite was run again after that change. The speak and persona suites don't involve it.

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Held what it should hold | 42 of 42 tries | 42 of 42 tries |
| Promoted what it should promote | 69 of 78 | 72 of 78 |
| Used a promoted convention in a later message | 23 of 35 (66% [40–85]) | 29 of 42 (69% [43–87]) |
| The same, before lessons were kept | 2 of 32 | 0 of 26 |

- Before any correction, the models used the convention in 0 of 84 tries, so what they say afterwards was taught.
- Most remaining misses come from two scenarios. Asked what to pick for "movie night this thursday", it usually doesn't call it Bad Film Thursday (1 of 12). Asked to rate a film it hasn't seen, it asks back in popcorns but rarely gives a rating itself (2 of 11).
- No troll's, bystander's or walked-away correction got through, before or after the change. Of the 15 tries held that should have promoted, the reaction judge refused 6 corrections (all on gpt-6-luna), 5 deepseek verdicts were lost to garbled output, and 4 failed at the retry step.
- During deepseek's English run, the reaction judge's JSON came back garbled 24 times, with the model's reasoning leaking into the keys. Asking again, which this change adds, recovered 18. The other runs had none.
- The style scenarios can't show much: the models already followed those styles in 56 of 72 tries before any correction, and in 66 after.

## What this doesn't show

These results cover one character on two models, on cases we wrote and labelled ourselves. A model judge is not a person, and the two judges here often disagreed on the persona pairs. Opus 5.5 judged outside `personagent eval`, reading the pairs in batches of about 116 per session, as each report's `rejudged` field records. Other models, especially small ones, may do worse.

## Files

Each model has a folder:

| File | What it holds |
|---|---|
| `speak-<lang>.json` | Every moment, every try, the reply or silence, and the label |
| `persona-<lang>.json` | Both replies, Opus's two picks, and Haiku's verdict under `earlier` |
| `learning-<lang>.json` | The run with lessons: each reaction, the candidates and their lessons, and the probe replies before and after |
| `learning-<lang>-before-lessons.json` | The first run, before lessons were kept |

To run the suites yourself, see [Measure it](../../guide.md#measure-it). `--rejudge` judges a report again with another model.
