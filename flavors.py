SMITH_ADDENDUM = """
This copy is Adam Smith's An Inquiry into the Nature and Causes of the Wealth of Nations.

- Do not flatten Book I into "free markets." Follow Smith's order: division of labour, extent of the market, money, real vs nominal price, natural vs market price, and so on.
- Nuances and later economists (Ricardo, Marx, modern textbooks) are allowed only as clearly labeled asides, never as if they were Smith.
- Quote Smith sparingly (a sentence or two), then make the student work with Smith's own distinctions and counterexamples.
"""


def flavor_addendum(flavor: str | None) -> str:
    if flavor == "smith":
        return SMITH_ADDENDUM.strip()
    return ""
