import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

const IDEAS = [
  {
    pri: "P0",
    area: "Memory",
    idea: "Stop injecting summaries into the visible thread",
    why: "Four system summaries appeared as student messages; two still thought you were taking the Introduction quiz while you were on knives.",
  },
  {
    pri: "P0",
    area: "Citations",
    idea: "Show Book / Chapter / paragraph, not chap03:p0",
    why: "You had to leave the app to ask what the tag meant. Judgment citations are not even clickable.",
  },
  {
    pri: "P1",
    area: "Grading",
    idea: "Calibrate miss vs mastered; keep answers in the thread",
    why: "Thin first quiz scored 0%. Generic retest paraphrases scored 100% and unlocked the next chapter.",
  },
  {
    pri: "P1",
    area: "Pacing",
    idea: "Do not auto-start the next unit after a pass",
    why: "Mastery immediately jumped you into Book I. No landing, no choice to reread.",
  },
  {
    pri: "P1",
    area: "Coverage",
    idea: "Quiz only after the unit’s load-bearing claims are actually taught",
    why: "Chapter I has pin numbers, trifling vs great manufactures, and the woolen coat. You were tested after three short analogies.",
  },
  {
    pri: "P1",
    area: "Quiz UI",
    idea: "Keep the chat box during a test",
    why: "The quiz replaced the composer. You could not ask a clarifying question mid-test.",
  },
  {
    pri: "P2",
    area: "Pedagogy",
    idea: "Push analogies back onto Smith’s text",
    why: "Knife-sharpening and context-switching were excellent. The tutor said “Exactly” and moved on, then asked for a modern machine example.",
  },
  {
    pri: "P2",
    area: "Progress",
    idea: "Show concept checklist, not a 0% bar on an in-progress chapter",
    why: "Introduction is mastered; Chapter I still looks empty even after a full Socratic pass.",
  },
];

export default function TutorSessionReview() {
  const theme = useHostTheme();

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Session review: close-reading tutor</H1>
        <Text tone="secondary">
          Source: live LangGraph thread from this morning (Introduction mastered,
          Book I Chapter I in a quiz). Ideas are tied to that conversation, not a
          generic chatbot punch list.
        </Text>
      </Stack>

      <Row gap={24} wrap>
        <Stat value="8" label="Real student turns" />
        <Stat value="4" label="Injected summaries" tone="warning" />
        <Stat value="0% → 100%" label="Intro quiz then retest" />
        <Stat value="3 / 11" label="Chapter I paragraphs cited" tone="warning" />
      </Row>

      <Callout tone="warning" title="The conversation is being eaten">
        After the Introduction pass, the summarizer wrote “Previous conversation
        was too long to summarize,” then kept dropping fake student messages
        whose “next step” was still the Introduction quiz. Your knife example
        survived; the tutor’s working memory of it did not. Until that is fixed,
        longer chapters will feel amnesiac.
      </Callout>

      <H2>What you actually did</H2>
      <Table
        headers={["Beat", "You", "Product"]}
        columnAlign={["left", "left", "left"]}
        rowTone={["info", "warning", "danger", "success", "info", "warning"]}
        rows={[
          [
            "Introduction teach",
            "Thoughtful reply: machines, artisans, policy rewards.",
            "Lectured three concepts at once, then offered a test.",
          ],
          [
            "“read for test”",
            "Typo for ready.",
            "Quiz fired. Fields are two rows; answers collapse to “Submitted written answers.”",
          ],
          [
            "First quiz",
            "Q1 partial; Q2/Q3 one-liners (“AL”, “AI indutry”).",
            "Overall 0%. Two misses. Crushing, then a lecture restating the same three points.",
          ],
          [
            "Retest",
            "Clean paraphrases of the reteach, still no hunters/fishers contrast.",
            "100%, unlocked Chapter I, started teaching it in the same breath.",
          ],
          [
            "Chapter I Socratic",
            "Knife-sharpening (dexterity), context-switching (time), inventing a sharpener (machines).",
            "Said “Exactly” three times. Never sent you back to pin counts, trifling vs great manufactures, or who invents machines.",
          ],
          [
            "Chapter I quiz",
            "Still open.",
            "Auto-quiz after three short answers. Third question asks for a modern example — the opposite of close reading.",
          ],
        ]}
      />

      <H2>What already works</H2>
      <Text>
        The loop is real: you cannot skip ahead, a thin quiz does not unlock the
        next chapter, and the tutor will argue with a modern slogan. Your first
        Introduction answer treated Smith as an industrial-age machine theorist;
        the tutor correctly said skill and organization, not just mechanization.
        In Chapter I the one-question-at-a-time cadence was much better than the
        Introduction dump. Citations that do work will jump the reader. Keep
        that spine.
      </Text>

      <H2>Highest-leverage changes</H2>
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader trailing={<Pill size="sm" active>P0</Pill>}>
            Hide summaries; remember the unit
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                SummarizationMiddleware is set to fire at 8k tokens and keep 6
                messages. It is writing those summaries into the chat as if you
                typed them, and gpt-4o-mini is summarizing the wrong goal.
              </Text>
              <Text tone="secondary">
                Summarize per unit, keep the last Socratic exchange intact, and
                never render the summary bubble. The tutor can see a briefing;
                you should not.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm" active>P0</Pill>}>
            Human citations
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                `¶ chap03:p0` is an HTML id. Render `Book I · Ch. I · opening`
                (or ¶1), hover a one-line quote, click to highlight. Ban range
                tokens like `[@chap01:p1-@chap01:p3]` — they do not parse. Make
                judgment evidence use the same clickable tags.
              </Text>
              <Text tone="secondary">
                This is the same confusion that pulled you out of the lesson
                into this chat.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">P1</Pill>}>
            Grade the mechanism, not the vibe
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                Miss should mean wrong or empty. Partial should be the default
                for a one-sentence try. Mastered should require Smith’s
                mechanism (produce-to-consumers; skill vs number of useful
                labourers; the three circumstances of Ch. I). Do not score 0%
                when one concept is partial, and do not unlock on a paraphrase
                of the reteach.
              </Text>
              <Text tone="secondary">
                Keep the written answers visible in the thread. Right now the
                examiner sees them and you do not.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">P1</Pill>}>
            Finish the chapter before the quiz
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                Give each unit a claim checklist the tutor must hit (and you can
                see). For Chapter I that is at least: thesis; why trifling
                trades show it; pin factory numbers; three circumstances;
                workmen vs philosophers on machines; universal opulence / woolen
                coat. Do not call present_quiz until those are taught or you
                explicitly ask.
              </Text>
              <Text tone="secondary">
                Pause after a pass: “Introduction is internalized. Open Chapter
                I when you want.” Auto-advance feels like being marched.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Pedagogy: use your analogies, then pin them</H2>
      <Stack gap={8}>
        <Text>
          You learn by extending a running example (knives → context switch →
          inventing a machine). That is a feature. The tutor treated it as a
          checklist to tick. After “Exactly,” it should have asked: Smith’s pin
          maker who “could scarce make one pin in a day” — what is the analogous
          number here? Who does Smith say invents the machines, the workman or
          the philosopher? Why does he start with a trifling manufacture?
        </Text>
        <Text>
          Drop “using a modern example” from the distinguish question. Distinguishing
          is Smith vs a slogan, or workman-invented vs philosopher-invented
          machines — still inside the chapter.
        </Text>
      </Stack>

      <H3>Smaller surface fixes from the same session</H3>
      <Table
        headers={["Fix", "From this session"]}
        rows={[
          [
            "Keep composer during quiz",
            "You could not ask what a question meant without abandoning the test.",
          ],
          [
            "Taller answer fields; confirm if an answer is one line",
            "“AL” and “AI indutry” were submitted as full answers.",
          ],
          [
            "Accept “ready for test” typos in routing, not only in the model",
            "“read for test” happened to work because the teacher inferred it.",
          ],
          [
            "Concept chips on the TOC, not a 0% bar",
            "Chapter I is in progress with a gold sliver that still reads as empty.",
          ],
          [
            "Reset should confirm; add “reteach this unit” without wiping the book",
            "Reset progress is the only control, and it is nuclear.",
          ],
        ]}
      />

      <Divider />
      <Text size="small" tone="tertiary">
        Thread 01a04905-4513-7772-a1a2-d54ea22495a8 · 36 messages · mode test on
        chap03 · Introduction last_judgment overall 1.0 after a 0.0 fail.
        Source: LangGraph local server, 28 Aug 2026.
      </Text>
      <Text size="small" tone="quaternary" style={{ color: theme.text.quaternary }}>
        Suggested build order: memory, citations, grading/pacing, then claim
        checklist. The Socratic knife thread is the product working; everything
        else is getting in its way.
      </Text>
    </Stack>
  );
}
