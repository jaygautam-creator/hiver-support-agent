.PHONY: help setup data survey subsample taxonomy prelabel label judge-tool \
        repro repro-live anchoring agreement clean

help:
	@echo "REPRODUCE"
	@echo "  make repro         headline results, offline from committed cache (~1 min)"
	@echo "  make repro-live    same, re-issuing every LLM call (needs GOOGLE_API_KEY)"
	@echo ""
	@echo "ANALYSIS"
	@echo "  make anchoring     labelling anchoring measurement -> results/anchoring.md"
	@echo "  make agreement     LLM judge vs human -> results/judge_agreement.md"
	@echo ""
	@echo "REBUILD FROM RAW (optional; subsample is committed)"
	@echo "  make setup / data / survey / subsample / taxonomy"
	@echo ""
	@echo "LABELLING TOOLS"
	@echo "  make label         regenerate golden/label.html"
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

label: prelabel
	python3 -m scripts.make_labeller

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

clean:
	rm -rf results/*.md results/*.png results/errors/* results/predictions.jsonl
