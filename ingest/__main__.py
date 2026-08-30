from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from ingest.constants import ROOT

load_dotenv(ROOT / ".env")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest a copy into curriculum units.")
    parser.add_argument("--copy-id", help="Existing copies.id whose source is already in object storage.")
    parser.add_argument("--seed-demo", action="store_true", help="Seed the public Smith demo copy.")
    parser.add_argument(
        "--write-questions",
        action="store_true",
        help="Write per-unit exams onto an existing corpus without re-embedding.",
    )
    parser.add_argument("--force-questions", action="store_true", help="Regenerate exams even if present.")
    parser.add_argument("--embed", action="store_true", default=True)
    parser.add_argument("--no-embed", action="store_true")
    args = parser.parse_args(argv)
    embed = not args.no_embed
    if args.write_questions:
        from ingest.constants import DEMO_COPY_ID
        from ingest.pipeline import write_questions

        copy_id = args.copy_id or (DEMO_COPY_ID if args.seed_demo else None)
        if not copy_id:
            parser.error("--write-questions needs --copy-id or --seed-demo")
        print(write_questions(copy_id, force=args.force_questions))
        return
    if args.seed_demo:
        from ingest.pipeline import seed_demo

        result = seed_demo(embed=embed)
        print(result)
        return
    if args.copy_id:
        from ingest.pipeline import ingest_copy

        print(ingest_copy(args.copy_id, embed=embed))
        return
    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
