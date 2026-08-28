export type Paragraph = {
  type: "p";
  text: string;
  paragraph_id: string;
};

export type Unit = {
  id: string;
  source_chapter_id: string;
  book: string;
  book_title: string;
  title: string;
  part_title: string | null;
  order: number;
  word_count: number;
  paragraphs: Paragraph[];
  outline: string[];
};

export type Corpus = {
  book: { title: string; author: string };
  units: Unit[];
};

export type MasteryEntry = {
  unlocked?: boolean;
  score?: number;
  status?: string;
  concepts?: Array<{
    concept: string;
    score: "miss" | "partial" | "mastered";
    evidence: string;
    reteach_angle: string;
  }>;
};

export type QuizQuestion = {
  id: string;
  prompt: string;
  concept: string;
  kind: "explain" | "apply" | "distinguish";
};

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  avatarUrl: string;
};

export type BookProgress = {
  book: string;
  totalUnits: number;
  masteredUnits: number;
  totalWords: number;
  masteredWords: number;
  remainingWords: number;
};

export type ProgressPayload = {
  mastery: Record<string, MasteryEntry>;
  books: BookProgress[];
  remainingWords: number;
  remainingUnits: number;
  currentUnitId: string | null;
};

export type TutorState = {
  messages?: unknown[];
  current_chapter_id?: string;
  mode?: "teach" | "test" | "judge" | "revise";
  mastery?: Record<string, MasteryEntry>;
  open_quiz?: { questions: QuizQuestion[] } | null;
  weak_concepts?: string[];
  last_judgment?: {
    overall: number;
    summary_for_student: string;
    concepts: MasteryEntry["concepts"];
  } | null;
  copy_id?: string;
};
