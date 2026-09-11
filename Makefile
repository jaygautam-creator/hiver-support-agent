.PHONY: help setup data survey subsample taxonomy sample prelabel label judge-tool \
        merge test test-labeller test-judge-validator repro repro-live anchoring agreement \
        second-annotator validate-judge ablate operating-point two-stage check-report clean

help:
	@echo "REPRODUCE"
	@echo "  make repro         headline results, offline from committed cache (~1 min)"
	@echo "  make repro-live    same, re-issuing every LLM call (needs GOOGLE_API_KEY)"
	@echo ""
	@echo "ANALYSIS"
	@echo "  make anchoring     labelling anchoring measurement -> results/anchoring.md"
	@echo "  make agreement     LLM judge vs human -> results/judge_agreement.md"
	@echo "  make second-annotator  independent model relabels the golden set,"
	@echo "                     measuring how unambiguous the taxonomy is"
	@echo "  make validate-judge    4 automated judge checks -> results/judge_validation.md"
	@echo "  make ablate            k=0 retrieval ablation -> results/ablation_retrieval.md"
	@echo "  make operating-point   expected cost vs cost ratio -> results/operating_point.md"
	@echo "  make two-stage         decide-then-justify variant -> results/two_stage.md"
	@echo ""
	@echo "SELF-CHECK"
	@echo "  make check-report  verify README's quoted numbers against results/"
	@echo ""
	@echo "REBUILD FROM RAW (optional; subsample is committed)"
	@echo "  make setup / data / survey / subsample / taxonomy / sample"
	@echo ""
	@echo "LABELLING (round 2: the remaining 158, blind)"
	@echo "  make label         regenerate golden/label.html (blind, unlabelled only)"
	@echo "  make merge FILE=~/Downloads/labelled.jsonl   validate + merge an export"
	@echo "  make test          test both labelling tools' state machines"
	@echo "  make judge-tool    regenerate golden/judge_validation.html"

setup:
	python3 -m pip install -r requirements.txt

data:
	./scripts/download_data.sh

survey:
	python3 -m scripts.survey_brands
	python3 -m scripts.deflection_check

subsample:
	python3 -m src.data --brand AppleSupport

taxonomy:
	python3 -m scripts.derive_taxonomy

# Draws the 198-item golden sampling frame (natural + targeted strata).
# Seeded, so it reproduces exactly -- but re-running it after labelling has
# started would strand the existing labels, so it is not on any default path.
sample:
	python3 -m scripts.build_golden_sample

prelabel:
	python3 -m scripts.prelabel

# NOTE: no longer depends on `prelabel`. Round 2 is blind-only, so the tool is
# built without pre-labels at all; regenerating them is not part of the path.
label:
	python3 -m scripts.make_labeller

merge:
ifndef FILE
	$(error usage: make merge FILE=~/Downloads/labelled.jsonl)
endif
	python3 -m scripts.merge_labels $(FILE)

# The labelling tools are measurement apparatus: a silent bug in one does not
# crash anything, it just changes what the data means. Both have already done it.
test: test-labeller test-judge-validator

test-labeller:
	node tests/test_labeller.mjs

test-judge-validator:
	node tests/test_judge_validator.mjs

judge-tool:
	python3 -m scripts.make_judge_validator

# The grader's entrypoint. Replays committed LLM responses; a cache miss is a
# hard error, which proves the committed numbers came from the committed cache.
repro:
	CACHE_OFFLINE=1 python3 -m src.evaluate

repro-live:
	python3 -m src.evaluate

# The four automated checks that stand in for the missing human judge study.
# ~32 judge calls, so it is deliberately not part of `make repro`.
validate-judge:
	python3 -m scripts.validate_judge

# Re-runs the agent with NO retrieved examples. The prediction is written into
# the script's docstring before the run; all three of them failed.
ablate:
	python3 -m scripts.ablate_retrieval

# No LLM calls: reads the committed predictions and turns them into the cost
# question a support team actually asks.
operating-point:
	python3 -m scripts.operating_point

# Splits the single call into decide -> justify. 80 agent calls.
two-stage:
	python3 -m scripts.two_stage

# The README quotes generated numbers by hand, which is the one link in the
# chain a re-run can silently break. This pins the ones a reader would quote
# back at me. It has already caught a 0.595-reported-as-0.60 drift.
check-report:
	python3 -m scripts.check_report

anchoring:
	python3 -m scripts.measure_anchoring

agreement:
	python3 -m scripts.judge_agreement

# A different model FAMILY (Gemma, not Gemini) relabels the golden set from the
# same written definitions the human used. Not a human agreement study -- it
# measures whether the taxonomy is applicable, and produces a re-review queue.
second-annotator:
	python3 -m scripts.second_annotator

clean:
	rm -rf results/*.md results/*.png results/errors/* results/predictions.jsonl
