# Working together

This repository starts from the completed individual pilot and proposal v12. The group can use it as a reproducible starting point for the INFH5000 assignment. The existing proposal retains its original author details and individual-assignment framing; a group submission should be developed as a new document.

## First steps

1. Read the five-page main proposal and the result tables under `outputs/classical/`.
2. Read `docs/REPRODUCTION.md` and run the lightweight checks.
3. Download the experiment archives from the repository release when raw trajectories are needed.
4. Agree on the group research question and assign work through GitHub issues. Create a branch for each change and open a pull request for review.

Useful work areas are controller design, evaluation and failure analysis, urban interpretation, and figures/documentation. Roles are not assigned to particular people yet.

## Experiment practice

- Keep `configs/classical_frozen_20261102.json` and its referenced source files as the recorded baseline. A change to a frozen source intentionally invalidates the original hash checks. Make a new protocol and source snapshot for new experiments; do not rewrite historical hashes to make an old test pass.
- Use separate development and test conditions. Choose new output directories; evaluation scripts reject existing campaign directories.
- Keep failed and contact episodes. Report strict arrival and contact-free arrival separately.
- Compare on matched inputs and report which conditions enter timing comparisons. The zero-velocity ablation isolates velocity input more directly than a comparison with RPP-inspired control.
- Keep exploratory trials separate from frozen tests. Describe RPP-inspired and DWA-style implementations as adaptations.
- The bounded local-detour trigger and its proposed 120-run experiment have not been implemented. They are possible group work, not an existing result.

## Pull requests

Explain the change, the conditions used to evaluate it, and the observed result. Include relevant checks and link the output records. Keep asset downloads, environments and raw campaign directories outside Git. Publish substantial new experiment records as versioned release assets with hashes.

Add collaborators through the private repository's Settings → Collaborators once their GitHub usernames are available. No invitations have been sent by this setup.
