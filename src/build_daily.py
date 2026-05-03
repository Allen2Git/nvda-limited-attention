"""DEPRECATED — superseded by the final pipeline.

This file was part of an earlier iteration of the project (see the README
'Research journey' section). The final paper no longer depends on it.

For the final pipeline, use:
  src/analysis.py         # all regressions
  src/make_figures.py     # all figures
  src/make_paper.py       # final paper (docx)
  src/make_letter.py      # cover letter to the professor
  src/app.py              # Streamlit interactive dashboard
  src/econ.py             # OLS + HC1 helper (shared utility)
"""
raise RuntimeError(
    "build_daily.py is deprecated. See README 'Research journey' and use "
    "src/analysis.py for the final pipeline."
)
