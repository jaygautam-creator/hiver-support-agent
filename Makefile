.PHONY: help setup data survey subsample taxonomy prelabel label judge-tool \
        merge test test-labeller test-judge-validator repro repro-live anchoring agreement \
        second-annotator clean

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
	@echo ""
	@echo "REBUILD FROM RAW (optional; subsample is committed)"
	@echo "  make setup / data / survey / subsample / taxonomy"
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
