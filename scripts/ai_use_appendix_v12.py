"""Short AI-use statement, review dialogue and supporting screenshots."""
import json
from build_proposal import ROOT


def append_ai_record(d, operation):
    record = json.loads((operation / 'verbatim_exchange.json').read_text())
    excerpts = json.loads((operation / 'ai_evidence_sources_c.json').read_text())['excerpts']
    d.page()
    d.p('Appendix. Generative AI Use', 'Heading')
    d.p('I used ChatGPT and Codex (OpenAI) to assist with literature review, controller and evaluation code, local simulation experiments, metric calculations, plots, and English writing and formatting. I requested checks of arrival criteria and failure cases, questioned the choice of comparison methods, and asked for clearer explanations of the implemented module, results and proposed extension. I reviewed the proposal and requested revisions. I remain responsible for understanding and approving the submission.')
    d.p('User Prompt', 'Subheading')
    for paragraph in record['question'].split('\n\n'):
        if paragraph:
            d.p(paragraph, 'AIResponse')
    d.p('AI Response', 'Subheading')
    for paragraph in record['response'].split('\n\n'):
        if paragraph:
            d.p(paragraph, 'AIResponse')
    d.p('Additional Exchanges', 'Subheading')
    d.p('User: “' + excerpts['revision_user_1'] + '” “' + excerpts['revision_user_2'] + '”', 'AIResponse')
    d.p('Codex: “' + excerpts['revision_assistant_1'] + '” “' + excerpts['revision_assistant_2'] + '”', 'AIResponse')
    d.p('User: “' + excerpts['contribution_user'] + '”', 'AIResponse')
    d.p('Codex: “' + excerpts['contribution_assistant'] + '”', 'AIResponse')
    for i in (1, 2, 3):
        d.image(ROOT / f'outputs/editorial_v7_20261111/ai_screenshots/codex_original_{i:02d}.png', width=5.25 if i == 1 else 6.5)
