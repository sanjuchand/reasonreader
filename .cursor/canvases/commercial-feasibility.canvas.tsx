import {
  BarChart,
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
} from "cursor/canvas";

export default function CommercialFeasibility() {
  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <Row gap={8} align="center">
          <H1>The business (locked)</H1>
          <Pill active>Aug 2026</Pill>
        </Row>
        <Text weight="semibold">
          Bring a book you have the right to read. We tutor you through
          your copy. We do not become the library.
        </Text>
        <Text tone="secondary">
          Smith is the public demo so a visitor can try the loop without
          uploading. It is not the catalog, the brand, or the end state of
          the ingest pipeline.
        </Text>
      </Stack>

      <Callout
        tone="success"
        title="This sentence is the company. Everything else is implementation."
      >
        Two products in one surface: a shared Smith try-path, and a private
        tutor over the user’s own file. Mixing those — a class library of
        uploads, a global catalog of PDFs, homework answers — is a
        different company and a legal problem. The current repo is still
        only the Smith half.
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="7 / 10" label="This business, if shipped" tone="success" />
        <Stat value="4 / 10" label="If we become the library" tone="danger" />
        <Stat value="$12–20/mo" label="Price that now makes sense" />
        <Stat value="3 / 10" label="Repo vs locked thesis" tone="warning" />
      </Grid>

      <H2>Contract</H2>
      <Table
        headers={["", "Means in the product"]}
        rows={[
          [
            "Bring a book you have the right to read",
            "Signed-in user uploads their copy. We do not verify title ownership in software, but we design as if the file is theirs alone. Public domain Smith needs no upload.",
          ],
          [
            "We tutor you through your copy",
            "Curriculum, reader, citations, and progress are bound to that file. Mastery of their book, not a shared edition.",
          ],
          [
            "We do not become the library",
            "No sharing the file. No class shelf. No ‘upload once, seminar reads here.’ No replacing the bookstore. DMCA on us, not a catalog.",
          ],
          [
            "Smith is the public demo",
            "Zero-upload try path. Same loop. Demo flavor may mention Smith; ingest and prompts must not stay Smith-only.",
          ],
        ]}
        rowTone={["info", "success", "danger", "neutral"]}
      />

      <Stack gap={8}>
        <H2>Demand is large. The buyer who pays is not the student dumping a PDF.</H2>
        <Text>
          Anyone assigned a hard book wants a tutor. Most of them want
          answers. This product refuses that — it makes them internalize the
          argument and pass a gate. That is pedagogically the whole point
          and commercially a filter: you lose the cheating market on
          purpose, and you keep parents, autodidacts, professors, and
          professionals who actually want the book finished.
        </Text>
      </Stack>

      <Table
        headers={["Buyer", "Job to be done", "Will they pay?", "Fit"]}
        rows={[
          [
            "Autodidact / professional",
            "Finish the O'Reilly book / philosophy text they keep abandoning",
            "Yes, $12–20/mo if it beats NotebookLM at finishing",
            "Best consumer fit",
          ],
          [
            "Parent / homeschool",
            "Child must pass units in the assigned book",
            "Yes — they already buy curricula",
            "Best distribution",
          ],
          [
            "Professor (open / PD text)",
            "Assigned reading with evidence of close reading",
            "Maybe — seat license if it reduces grading theater",
            "High leverage, slow",
          ],
          [
            "College student + pirated textbook",
            "Pass the exam with least reading",
            "They will use it if free; they want answers",
            "Largest demand, worst customer",
          ],
          [
            "Company (own docs)",
            "Handbook / policy / onboarding as a tutor",
            "Yes, if you sell seats not ‘books’",
            "Clean IP, different company",
          ],
        ]}
        rowTone={["success", "success", "info", "danger", "neutral"]}
      />

      <H2>Who you actually compete with</H2>
      <Text>
        Not Khanmigo (curriculum they own) and not Brilliant (they write
        the lessons). You compete with every “chat with this file” product,
        which is now free and good enough for Q&A.
      </Text>
      <Table
        headers={["Substitute", "What it does", "Where you must beat it"]}
        rows={[
          [
            "NotebookLM / Gemini",
            "Upload sources, ask, get audio overviews",
            "Units, gates, citations into a reader, ‘you have not mastered this yet’",
          ],
          [
            "ChatGPT / Claude projects",
            "File upload, Socratic if prompted, no memory of a curriculum",
            "The curriculum is the product. A prompt is not a course.",
          ],
          [
            "Quizlet / Knowt / Anki",
            "Flashcards from a PDF",
            "Close reading of an argument, not term lists",
          ],
          [
            "Human tutor / office hours",
            "Expensive, scarce, actually demanding",
            "Price. You will not beat quality until the judge is calibrated.",
          ],
        ]}
      />
      <Text size="small" tone="tertiary">
        If a user can get 80% of the value by uploading the same PDF to
        NotebookLM, they will not pay you. Differentiation has to show up
        in the first session: a unit list from their file, a tutor that
        will not skip ahead, a test they asked for.
      </Text>

      <H2>Copyright is the business-model constraint, not a footnote</H2>
      <Text>
        BYOB demand is copyrighted textbooks. Hosting those files for
        anyone but the uploader — or hosting copies the user does not own —
        is how this company dies. Training-on-books case law (e.g. Bartz v.
        Anthropic) does not bless a permanent library of pirated PDFs. A
        professor sharing one uploaded Mankiw with a class is the feature
        schools will ask for and the one you must refuse.
      </Text>
      <Grid columns={2} gap={16}>
        <Stack gap={8}>
          <H3>Safe enough to ship</H3>
          <Text>
            Public domain and open textbooks (Gutenberg, OpenStax).
            User-private upload of a copy they own, never shared, DMCA
            takedown, no training on uploads. Company-owned manuals.
            Author/publisher who wants a tutor for their book.
          </Text>
        </Stack>
        <Stack gap={8}>
          <H3>Looks like growth, is a lawsuit</H3>
          <Text>
            LibGen/Anna’s Archive dumps. “Upload once, whole seminar
            reads it here.” Replacing the textbook so students do not
            buy it. That last one is exactly the market-substitution
            fact pattern publishers sue over.
          </Text>
        </Stack>
      </Grid>
      <Callout tone="warning" title="The feature we will be asked for and must refuse">
        A professor wants one PDF, twenty students, progress for the
        whole room. That is a library. The allowed version: each student
        brings their own legally obtained copy, or the course uses an
        open/public text (including Smith). The assigner sees mastery,
        not the file.
      </Callout>

      <H2>This repo vs that product</H2>
      <Table
        headers={["Capability", "BYOB needs", "Today"]}
        rows={[
          [
            "Ingest",
            "PDF / EPUB / HTML; heading detection; junk-page skip (TOC, copyright)",
            "Gutenberg div.chapter HTML only",
          ],
          [
            "Tutor voice",
            "Generic: internalize this author’s argument, in this order",
            "Hard-coded Smith, Ricardo/Marx asides, Book I sequence",
          ],
          [
            "Library",
            "Many books per user, switch, progress per title",
            "One corpus, one thread per user",
          ],
          [
            "Citations",
            "Stable ids into the user’s file; reader for that file",
            "Works — for Smith’s HTML",
          ],
          [
            "Mastery loop",
            "Teach / test / judge / reteach, student-initiated quiz",
            "Built. Judge still miscalibrated in the live session.",
          ],
        ]}
        rowTone={["danger", "danger", "warning", "success", "warning"]}
      />

      <H2>Unit economics (still gpt-4o)</H2>
      <Text>
        Ingest is cheap (embed a book once per user). Tutoring is the
        cost. A flat unlimited-books plan without a cap is how power
        users sink you. Assumptions unchanged: ~$0.40–1.20 per unit on
        gpt-4o; teach should move to a smaller model.
      </Text>
      <Table
        headers={["Pattern", "Est. monthly LLM COGS", "On a $16/mo plan"]}
        rows={[
          ["One hard book, 8 units", "$4–10", "OK if most users are this"],
          ["Three books, light sampling", "$8–20", "Need a cap or cheaper teach"],
          ["Finishes a 100-unit textbook", "$40–80 that month", "Loss — meter or pause"],
        ]}
        rowTone={["success", "warning", "danger"]}
      />
      <Text size="small" tone="tertiary">
        Price against NotebookLM Plus (~$20-tier Google AI) and ChatGPT
        Plus, not against Khanmigo’s $4. You are a reading product with
        model cost, not a nonprofit add-on.
      </Text>

      <H2>Modeled 24-month ARR by GTM</H2>
      <BarChart
        horizontal
        height={240}
        categories={[
          "Consumer BYOB, PD + private upload",
          "Homeschool / parent assigns the book",
          "Open-textbook course seats",
          "Student PDF helper (ignore copyright)",
        ]}
        series={[
          {
            name: "Conservative ARR ($k)",
            data: [80, 150, 40, 0],
            tone: "neutral",
          },
          {
            name: "Upside ARR ($k)",
            data: [400, 800, 250, 0],
            tone: "info",
          },
        ]}
        yMin={0}
        yMax={900}
      />
      <Text size="small" tone="tertiary">
        Thousands of USD, scenario only. Homework-helper is plotted at
        zero because it is not a business you should take — growth would
        be real and radioactive. District/K-12 still omitted: FERPA and
        a sales team you do not have.
      </Text>

      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Pill size="sm" active>Ship</Pill>}>
            Consumer + Smith demo
          </CardHeader>
          <CardBody>
            <Text>
              Public Smith as the try-before-upload. Paid: your own
              books, private, usage-capped. This is the honest v1.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">Next</Pill>}>
            Assigner as customer
          </CardHeader>
          <CardBody>
            <Text>
              Parent or professor picks the file (or an open text).
              Learner cannot skip units. Progress is the report card.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">Later</Pill>}>
            Publisher / author
          </CardHeader>
          <CardBody>
            <Text>
              Official tutor edition of a living book. Slow BD, actual
              moat. Do not wait for this to validate the loop.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={8}>
        <H2>Moat, restated</H2>
        <Text>
          Files are not a moat. Chat-with-PDF is not a moat. The scarce
          piece is a tutor that extracts a curriculum from an arbitrary
          book and will not let the student fake it. That requires a
          judge people trust — which failed once already (0% then 100%
          on paraphrases) — and ingest that does not fall over on a
          scanned textbook. Copying the LangGraph graph is easy.
          Copying taste in unit-splitting and refusal to skip is the
          product.
        </Text>
      </Stack>

      <H2>What has to be true before taking payment</H2>
      <Table
        headers={["Gate", "Bar", "Today"]}
        rows={[
          [
            "Generic ingest",
            "A second book (PDF or EPUB) produces usable units without a Smith parser",
            "One HTML dialect",
          ],
          [
            "Generic tutor",
            "Prompt is ‘this author’s argument,’ not Adam Smith",
            "Smith-only system prompt",
          ],
          [
            "Judge",
            "Human rater agrees; empty/thin answers fail; paraphrase of the text is not an A",
            "Known miss",
          ],
          [
            "Copyright UX",
            "Private-by-default, no class-share of the file, DMCA path",
            "Not designed",
          ],
          [
            "First-session test",
            "Upload → unit list → one Socratic pass → student-asked quiz, under 15 minutes",
            "Local Smith demo only",
          ],
        ]}
        rowTone={["danger", "danger", "danger", "warning", "warning"]}
      />

      <Divider />

      <Callout tone="info" title="Kill criteria (90 days after BYOB ingest works)">
        If people upload a book and then only chat — never take a test,
        never pass a unit — you are a worse NotebookLM. Kill or change
        the loop. If they do pass units on books they chose, you have a
        business. Do not measure success in Smith completions.
      </Callout>

      <Text size="small" tone="tertiary">
        ARR and COGS are scenario models from public tutor pricing,
        NotebookLM as the free substitute, and this repo (gpt-4o
        teach/judge, Smith-specific ingest). Not measured revenue. Not
        legal advice on copyright.
      </Text>
    </Stack>
  );
}
