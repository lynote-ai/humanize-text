# Recipe 使用 Bash。
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# 保持工作区与发布包不产生 Python bytecode 缓存。
export PYTHONDONTWRITEBYTECODE := 1

# 本地默认使用项目约定的 Conda 环境；CI 可通过 PYTHON=python 覆盖。
PYTHON ?= conda run --no-capture-output -n test python
# 开源项目根目录。
PROJECT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
# 开源项目 manifest。
MANIFEST := $(PROJECT_DIR)/manifest.yaml
# 公开 demo 根目录与登记文件。
DEMO_ROOT := $(PROJECT_DIR)/data/demos
DEMO_MANIFEST := $(DEMO_ROOT)/manifest.yaml
# 对外展示的 5 个 System Prompt 示例。
PROMPT_EXAMPLES := $(PROJECT_DIR)/configs/system_prompt_examples_5.json
# 完整源产物目录；仅 demo 打包时由维护者显式传入。
SOURCE_ARTIFACT_DIR ?=
# 内部导出时使用的私有来源原始标签；不设置公开默认值。
INTERNAL_SOURCE_NAME ?=

# 用户提供的上游 SFT manifest、bundle 和其中的 artifact ID。
SOURCE_MANIFEST ?=
SOURCE_BUNDLE ?=
SOURCE_ARTIFACT_ID ?=
# 固定的分层预留策略。
RESERVATION_CONFIG ?= configs/sft_kto_reservation_v1.yaml
# 新产物根目录；所有构建脚本会创建时间戳子目录。
OUTPUT_DIR ?= artifacts
# 已构建的 reservation bundle；后续阶段必须显式指定。
RESERVATION_BUNDLE ?=
# 已构建的 KTO bundle；独立校验时必须显式指定。
KTO_BUNDLE ?=

# OpenAI-compatible 候选生成服务参数。
GENERATION_BASE_URL ?=
GENERATION_MODEL ?=
GENERATION_ROUNDS ?= 2
GENERATION_NUM_RESULTS ?= 6
GENERATION_TEMPERATURES ?= 0.3,0.5,0.7,0.9,1.0,1.0
GENERATION_MAX_TOKENS ?= 4096
GENERATION_WORKERS ?= 8
GENERATION_CHUNK_SIZE ?= 50
GENERATION_MAX_RETRIES ?= 3
GENERATION_LIMIT_PER_SPLIT ?= -1
GENERATION_OUTPUT_DIR ?= artifacts
GENERATION_RESUME_BUNDLE ?=
GENERATION_RESUME_ARG := $(if $(GENERATION_RESUME_BUNDLE),--resume-bundle "$(GENERATION_RESUME_BUNDLE)",)

# KTO 负例选择输入、策略及输出目录。
KTO_TRAIN_CANDIDATES ?=
KTO_VALIDATION_CANDIDATES ?=
KTO_SELECTOR_CONFIG ?= configs/kto_negative_selector_v1.yaml
KTO_OUTPUT_DIR ?= artifacts
# 结构优先刷新策略及输出目录。
KTO_REFRESH_CONFIG ?= configs/kto_structure_refresh_v2.yaml
KTO_REFRESH_OUTPUT_DIR ?= artifacts

# 模型调用必须显式声明远程执行并授权请求。
EXECUTION_ENV ?= local
ALLOW_REMOTE_MODEL_CALLS ?= 0

.PHONY: help env-check manifest-validate demo-validate docs-validate demo-export test check \
	source-args-check reservation-inspect reservation-build reservation-validate \
	kto-candidate-generate kto-negative-inspect kto-negative-build \
	kto-negative-validate kto-refresh-build

help:
	@printf '%s\n' \
	  'env-check                         Validate the Python runtime' \
	  'manifest-validate                 Validate the project manifest' \
	  'demo-validate                     Enforce 50 records per stage and exactly 5 Prompt examples' \
	  'docs-validate                     Validate bilingual docs, local links, and Mermaid blocks' \
	  'test                              Run local unit tests' \
	  'check                             Run manifest, demo, docs, and unit-test validation' \
	  'reservation-inspect               Inspect source/length supply without writing data' \
	  'reservation-build                 Build disjoint SFT data and KTO generation seeds' \
	  'reservation-validate              Validate BUNDLE=<path>' \
	  '  SOURCE_MANIFEST=<path> SOURCE_BUNDLE=<path> SOURCE_ARTIFACT_ID=<id> (required)' \
	  'kto-candidate-generate            Generate candidates with an OpenAI-compatible remote service' \
	  '  RESERVATION_BUNDLE=<path> GENERATION_BASE_URL=<url> GENERATION_MODEL=<model> (required)' \
	  '  Requires EXECUTION_ENV=remote ALLOW_REMOTE_MODEL_CALLS=1' \
	  'kto-negative-inspect               Inspect candidate defect supply without writing data' \
	  'kto-negative-build                 Build balanced KTO rows and a review sample' \
	  '  RESERVATION_BUNDLE=<path> KTO_TRAIN_CANDIDATES=<path> KTO_VALIDATION_CANDIDATES=<path> (required)' \
	  'kto-negative-validate              Validate KTO_BUNDLE=<path>' \
	  'kto-refresh-build                  Build the 60/20/20 structure-first KTO refresh bundle' \
	  'demo-export                        Re-export exactly 50 demos per stage (maintainer-only)' \
	  '  SOURCE_ARTIFACT_DIR=<path> INTERNAL_SOURCE_NAME=<label> (required)'

env-check:
	@$(PYTHON) --version

manifest-validate: env-check
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_manifest.py --manifest manifest.yaml

demo-validate: env-check
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_demo_data.py \
	  --demo-root data/demos --manifest data/demos/manifest.yaml \
	  --prompt-examples configs/system_prompt_examples_5.json

docs-validate: env-check
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_docs.py --project-dir .

test: env-check
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) -m unittest discover \
	  -s code/tests -p 'test_*.py'

check: manifest-validate demo-validate docs-validate test

# SOURCE_ARTIFACT_DIR：完整源产物目录；仅维护者打包 demo 时使用。
demo-export: env-check
	@test -n "$(SOURCE_ARTIFACT_DIR)" || { echo 'SOURCE_ARTIFACT_DIR is required'; exit 2; }
	@test -n "$(INTERNAL_SOURCE_NAME)" || { echo 'INTERNAL_SOURCE_NAME is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && $(PYTHON) tools/export_release.py \
	  --source-artifact-dir "$(SOURCE_ARTIFACT_DIR)" --project-dir "$(PROJECT_DIR)" \
	  --internal-source-name "$(INTERNAL_SOURCE_NAME)"

source-args-check:
	@test -n "$(SOURCE_MANIFEST)" || { echo 'SOURCE_MANIFEST is required'; exit 2; }
	@test -n "$(SOURCE_BUNDLE)" || { echo 'SOURCE_BUNDLE is required'; exit 2; }
	@test -n "$(SOURCE_ARTIFACT_ID)" || { echo 'SOURCE_ARTIFACT_ID is required'; exit 2; }

reservation-inspect: manifest-validate source-args-check
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/a_reserve_sft_for_kto.py \
	  --manifest manifest.yaml --source-manifest "$(SOURCE_MANIFEST)" \
	  --source-bundle "$(SOURCE_BUNDLE)" --source-artifact-id "$(SOURCE_ARTIFACT_ID)" \
	  --config "$(RESERVATION_CONFIG)" --output-dir "$(OUTPUT_DIR)" --inspect-only

# --require-writable：released 项目快照禁止启动写盘构建。
reservation-build: manifest-validate source-args-check
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_manifest.py \
	  --manifest manifest.yaml --require-writable
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/a_reserve_sft_for_kto.py \
	  --manifest manifest.yaml --source-manifest "$(SOURCE_MANIFEST)" \
	  --source-bundle "$(SOURCE_BUNDLE)" --source-artifact-id "$(SOURCE_ARTIFACT_ID)" \
	  --config "$(RESERVATION_CONFIG)" --output-dir "$(OUTPUT_DIR)"

# BUNDLE：需要独立复核的 reservation bundle。
reservation-validate: manifest-validate source-args-check
	@test -n "$(BUNDLE)" || { echo 'BUNDLE is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/b_validate_sft_kto_reservation.py \
	  --manifest manifest.yaml --source-manifest "$(SOURCE_MANIFEST)" \
	  --source-bundle "$(SOURCE_BUNDLE)" --source-artifact-id "$(SOURCE_ARTIFACT_ID)" \
	  --config "$(RESERVATION_CONFIG)" --bundle "$(BUNDLE)"

# 远程模型调用保护：默认拒绝，避免误发批量请求。
kto-candidate-generate: manifest-validate
	@test -n "$(RESERVATION_BUNDLE)" || { echo 'RESERVATION_BUNDLE is required'; exit 2; }
	@test -n "$(GENERATION_BASE_URL)" || { echo 'GENERATION_BASE_URL is required'; exit 2; }
	@test -n "$(GENERATION_MODEL)" || { echo 'GENERATION_MODEL is required'; exit 2; }
	@test "$(EXECUTION_ENV)" = "remote" || { echo 'EXECUTION_ENV=remote is required'; exit 2; }
	@test "$(ALLOW_REMOTE_MODEL_CALLS)" = "1" || { echo 'ALLOW_REMOTE_MODEL_CALLS=1 is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/c_generate_kto_candidates.py \
	  --manifest manifest.yaml \
	  --train-input "$(RESERVATION_BUNDLE)/kto_train_seed.jsonl" \
	  --validation-input "$(RESERVATION_BUNDLE)/kto_validation_seed.jsonl" \
	  --output-dir "$(GENERATION_OUTPUT_DIR)" --base-url "$(GENERATION_BASE_URL)" \
	  --model "$(GENERATION_MODEL)" --rounds "$(GENERATION_ROUNDS)" \
	  --num-results "$(GENERATION_NUM_RESULTS)" --temperatures "$(GENERATION_TEMPERATURES)" \
	  --max-tokens "$(GENERATION_MAX_TOKENS)" --workers "$(GENERATION_WORKERS)" \
	  --chunk-size "$(GENERATION_CHUNK_SIZE)" --max-retries "$(GENERATION_MAX_RETRIES)" \
	  --limit-per-split "$(GENERATION_LIMIT_PER_SPLIT)" $(GENERATION_RESUME_ARG)

kto-negative-inspect: manifest-validate
	@test -n "$(RESERVATION_BUNDLE)" || { echo 'RESERVATION_BUNDLE is required'; exit 2; }
	@test -n "$(KTO_TRAIN_CANDIDATES)" || { echo 'KTO_TRAIN_CANDIDATES is required'; exit 2; }
	@test -n "$(KTO_VALIDATION_CANDIDATES)" || { echo 'KTO_VALIDATION_CANDIDATES is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/d_select_kto_negatives.py \
	  --manifest manifest.yaml \
	  --train-seed "$(RESERVATION_BUNDLE)/kto_train_seed.jsonl" \
	  --validation-seed "$(RESERVATION_BUNDLE)/kto_validation_seed.jsonl" \
	  --train-candidates "$(KTO_TRAIN_CANDIDATES)" \
	  --validation-candidates "$(KTO_VALIDATION_CANDIDATES)" \
	  --config "$(KTO_SELECTOR_CONFIG)" --output-dir "$(KTO_OUTPUT_DIR)" --inspect-only

# --require-writable：released 项目快照禁止启动写盘构建。
kto-negative-build: manifest-validate
	@test -n "$(RESERVATION_BUNDLE)" || { echo 'RESERVATION_BUNDLE is required'; exit 2; }
	@test -n "$(KTO_TRAIN_CANDIDATES)" || { echo 'KTO_TRAIN_CANDIDATES is required'; exit 2; }
	@test -n "$(KTO_VALIDATION_CANDIDATES)" || { echo 'KTO_VALIDATION_CANDIDATES is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_manifest.py \
	  --manifest manifest.yaml --require-writable
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/d_select_kto_negatives.py \
	  --manifest manifest.yaml \
	  --train-seed "$(RESERVATION_BUNDLE)/kto_train_seed.jsonl" \
	  --validation-seed "$(RESERVATION_BUNDLE)/kto_validation_seed.jsonl" \
	  --train-candidates "$(KTO_TRAIN_CANDIDATES)" \
	  --validation-candidates "$(KTO_VALIDATION_CANDIDATES)" \
	  --config "$(KTO_SELECTOR_CONFIG)" --output-dir "$(KTO_OUTPUT_DIR)"

# KTO_BUNDLE：需要独立复核的已构建 KTO bundle。
kto-negative-validate: manifest-validate
	@test -n "$(KTO_BUNDLE)" || { echo 'KTO_BUNDLE is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/e_validate_kto_dataset.py \
	  --manifest manifest.yaml --bundle "$(KTO_BUNDLE)"

kto-refresh-build: manifest-validate
	@test -n "$(RESERVATION_BUNDLE)" || { echo 'RESERVATION_BUNDLE is required'; exit 2; }
	@cd "$(PROJECT_DIR)" && $(PYTHON) code/harness/validate_manifest.py \
	  --manifest manifest.yaml --require-writable
	@cd "$(PROJECT_DIR)" && PYTHONPATH=code $(PYTHON) \
	  code/data_process/f_build_structure_first_kto_refresh.py \
	  --manifest manifest.yaml --config "$(KTO_REFRESH_CONFIG)" \
	  --train-seed "$(RESERVATION_BUNDLE)/kto_train_seed.jsonl" \
	  --validation-seed "$(RESERVATION_BUNDLE)/kto_validation_seed.jsonl" \
	  --train-candidates "$(RESERVATION_BUNDLE)/kto_train_candidates.jsonl" \
	  --validation-candidates "$(RESERVATION_BUNDLE)/kto_validation_candidates.jsonl" \
	  --output-dir "$(KTO_REFRESH_OUTPUT_DIR)"
