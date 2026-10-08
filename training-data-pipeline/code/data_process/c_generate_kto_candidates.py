"""Generate multiple rewrite candidates for both KTO seed splits via remote vLLM."""

import argparse
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any

from tqdm import tqdm
import yaml


OUTPUT_NAMES = {
    "train": "kto_train_candidates.jsonl",
    "validation": "kto_validation_candidates.jsonl",
}


def parse_args() -> argparse.Namespace:
    """Parse arguments supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--train-input", required=True, type=Path)
    parser.add_argument("--validation-input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--resume-bundle", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--rounds", required=True, type=int)
    parser.add_argument("--num-results", required=True, type=int)
    parser.add_argument(
        "--temperatures",
        required=True,
        help="Comma-separated temperatures, one entry per generated candidate chain.",
    )
    parser.add_argument("--max-tokens", required=True, type=int)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--chunk-size", required=True, type=int)
    parser.add_argument("--max-retries", required=True, type=int)
    parser.add_argument("--limit-per-split", required=True, type=int)
    return parser.parse_args()


def load_yaml_mapping(path: Path, description: str) -> dict[str, object]:
    """Load one required YAML mapping."""
    if not path.is_file():
        raise ValueError(f"{description} does not exist: {path}")
    with path.open("r", encoding="utf-8") as input_file:
        value = yaml.safe_load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping")
    return value


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_rewrite(text: str) -> str:
    """Trim model boundary whitespace without destroying paragraph structure."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("model returned an empty rewrite")
    return cleaned


def validate_seed_record(
    record: Mapping[str, object],
    expected_split: str,
    line_number: int,
) -> tuple[str, str]:
    """Validate one KTO seed and return its system prompt and source text."""
    required = {
        "input_id",
        "source",
        "split",
        "length_bucket",
        "ai_word_count",
        "human_word_count",
        "messages",
        "desirable_response",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "system_prompt_id",
    }
    if set(record) != required:
        raise ValueError(f"invalid seed fields at {expected_split} line {line_number}")
    if record["split"] != expected_split:
        raise ValueError(f"seed split mismatch at {expected_split} line {line_number}")
    messages = record["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError(f"seed messages must contain system/user at line {line_number}")
    if not all(isinstance(message, dict) for message in messages):
        raise ValueError(f"seed messages must be mappings at line {line_number}")
    if [message.get("role") for message in messages] != ["system", "user"]:
        raise ValueError(f"seed roles are invalid at line {line_number}")
    system_prompt = messages[0].get("content")
    input_text = messages[1].get("content")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError(f"empty system prompt at line {line_number}")
    if not isinstance(input_text, str) or not input_text.strip():
        raise ValueError(f"empty input text at line {line_number}")
    for name in ("input_id", "pair_sha256", "source_sha256", "target_sha256"):
        if not isinstance(record[name], str) or not str(record[name]).strip():
            raise ValueError(f"invalid {name} at line {line_number}")
    return system_prompt, input_text


def iter_seed_records(
    path: Path,
    expected_split: str,
) -> Iterator[tuple[int, dict[str, object], str, str]]:
    """Stream validated KTO seeds without loading a full split into memory."""
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                raise ValueError(f"blank seed line at {expected_split}:{line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid seed JSON at {expected_split}:{line_number}: {error}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"seed line must be a mapping at {line_number}")
            system_prompt, input_text = validate_seed_record(
                record, expected_split, line_number
            )
            yield line_number, record, system_prompt, input_text


def source_metadata(path: Path, split: str) -> dict[str, object]:
    """Validate and count one input split while computing its immutable hash."""
    count = sum(1 for _item in iter_seed_records(path, split))
    return {
        "path": str(path.resolve()),
        "record_count": count,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_temperature_schedule(raw_value: str, num_results: int) -> tuple[float, ...]:
    """Parse and validate one temperature entry per candidate chain."""
    try:
        temperatures = tuple(float(value.strip()) for value in raw_value.split(","))
    except ValueError as error:
        raise ValueError("temperatures must be comma-separated numbers") from error
    if len(temperatures) != num_results:
        raise ValueError(
            f"temperature count {len(temperatures)} must equal num-results {num_results}"
        )
    if any(temperature < 0 or temperature > 2 for temperature in temperatures):
        raise ValueError("candidate temperatures must be between 0 and 2")
    return temperatures


def validate_parameters(args: argparse.Namespace) -> None:
    """Reject unsafe or nonsensical generation settings before any API request."""
    if args.rounds <= 0 or args.num_results <= 0:
        raise ValueError("rounds and num-results must be positive")
    if args.max_tokens <= 0 or args.workers <= 0 or args.chunk_size <= 0:
        raise ValueError("max-tokens, workers, and chunk-size must be positive")
    if args.max_retries < 0:
        raise ValueError("max-retries must be non-negative")
    parse_temperature_schedule(args.temperatures, args.num_results)
    if not args.base_url.startswith(("http://", "https://")):
        raise ValueError("base-url must be HTTP or HTTPS")
    if not args.model.strip():
        raise ValueError("model must be non-empty")


def create_client(base_url: str, workers: int) -> Any:
    """Create one thread-safe OpenAI client only in the authorized remote run."""
    try:
        import httpx
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("remote generation requires the existing httpx and openai packages") from error
    return OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"),
        base_url=base_url,
        http_client=httpx.Client(
            verify=True,
            timeout=httpx.Timeout(600.0),
            limits=httpx.Limits(
                max_connections=max(workers * 2, 32),
                max_keepalive_connections=max(workers, 16),
            ),
        ),
    )


def rewrite_once(
    client: Any,
    model: str,
    system_prompt: str,
    text: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Call the remote model once, retrying transient failures deterministically."""
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                stream=False,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            return clean_rewrite(response.choices[0].message.content or "")
        except Exception:
            if attempt >= max_retries:
                raise
            time.sleep(min(2**attempt, 30))
    raise RuntimeError("unreachable retry state")


def rewrite_chain(
    client: Any,
    model: str,
    system_prompt: str,
    text: str,
    rounds: int,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Run one chained rewrite, feeding each output into the next round."""
    current = text
    for _round_index in range(rounds):
        current = rewrite_once(
            client,
            model,
            system_prompt,
            current,
            temperature,
            max_tokens,
            max_retries,
        )
    return current


def validate_candidate_record(
    record: Mapping[str, object],
    seed_record: Mapping[str, object],
    split: str,
    num_results: int,
    rounds: int | None = None,
    temperatures: Sequence[float] | None = None,
) -> None:
    """Validate one persisted candidate row against its source seed identity."""
    if record.get("input_id") != seed_record.get("input_id"):
        raise ValueError(f"candidate/input identity mismatch in {split}")
    if record.get("pair_sha256") != seed_record.get("pair_sha256"):
        raise ValueError(f"candidate/pair identity mismatch in {split}")
    if record.get("split") != split:
        raise ValueError(f"candidate split mismatch in {split}")
    if record.get("num_results") != num_results:
        raise ValueError(f"candidate num_results mismatch in {split}")
    if rounds is not None and record.get("rounds") != rounds:
        raise ValueError(f"candidate rounds mismatch in {split}")
    results = record.get("results")
    if not isinstance(results, list) or len(results) != num_results:
        raise ValueError(f"candidate result count mismatch in {split}")
    expected_ids = list(range(num_results))
    actual_ids = [result.get("chain_id") for result in results if isinstance(result, dict)]
    if actual_ids != expected_ids:
        raise ValueError(f"candidate chain IDs are incomplete in {split}")
    if any(
        not isinstance(result.get("rewrite"), str) or not result["rewrite"].strip()
        for result in results
        if isinstance(result, dict)
    ):
        raise ValueError(f"candidate rewrite is empty in {split}")
    if temperatures is not None:
        actual_temperatures = [
            result.get("temperature") for result in results if isinstance(result, dict)
        ]
        if actual_temperatures != list(temperatures):
            raise ValueError(f"candidate temperatures are incomplete in {split}")


def count_completed_prefix(
    input_path: Path,
    output_path: Path,
    split: str,
    num_results: int,
    rounds: int,
    temperatures: Sequence[float] | None = None,
) -> int:
    """Validate the exact completed prefix used for safe append-only resume."""
    if not output_path.exists():
        return 0
    seed_iterator = iter_seed_records(input_path, split)
    completed = 0
    with output_path.open("r", encoding="utf-8") as output_file:
        for line_number, line in enumerate(output_file, start=1):
            if not line.strip():
                raise ValueError(f"blank candidate output line at {split}:{line_number}")
            try:
                output_record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid candidate JSON at {split}:{line_number}; repair the tail before resume"
                ) from error
            if not isinstance(output_record, dict):
                raise ValueError(f"candidate output must be a mapping at {split}:{line_number}")
            try:
                _seed_line, seed_record, _system, _text = next(seed_iterator)
            except StopIteration as error:
                raise ValueError(f"candidate output exceeds {split} input") from error
            validate_candidate_record(
                output_record,
                seed_record,
                split,
                num_results,
                rounds,
                temperatures,
            )
            completed += 1
    return completed


def iter_chunks(
    input_path: Path,
    split: str,
    skip: int,
    limit: int,
    chunk_size: int,
) -> Iterator[list[tuple[dict[str, object], str, str]]]:
    """Yield bounded chunks after a validated completed prefix."""
    chunk: list[tuple[dict[str, object], str, str]] = []
    emitted = 0
    for index, (_line, record, system_prompt, input_text) in enumerate(
        iter_seed_records(input_path, split)
    ):
        if index < skip:
            continue
        if limit > 0 and emitted >= limit:
            break
        chunk.append((record, system_prompt, input_text))
        emitted += 1
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def process_split(
    client: Any,
    input_path: Path,
    output_path: Path,
    split: str,
    args: argparse.Namespace,
    expected_source_count: int,
) -> int:
    """Generate one split in bounded chunks and append only complete source records."""
    temperatures = parse_temperature_schedule(args.temperatures, args.num_results)
    completed = count_completed_prefix(
        input_path,
        output_path,
        split,
        args.num_results,
        args.rounds,
        temperatures,
    )
    if completed:
        print(f"[resume:{split}] validated {completed} completed input rows")
    remaining_source = expected_source_count - completed
    run_limit = (
        min(remaining_source, args.limit_per_split)
        if args.limit_per_split > 0
        else remaining_source
    )
    if run_limit <= 0:
        return completed
    chain_total = run_limit * args.num_results
    print(
        f"[run:{split}] inputs={run_limit} candidates={args.num_results} "
        f"rounds={args.rounds} requests={chain_total * args.rounds} workers={args.workers} "
        f"temperatures={','.join(str(value) for value in temperatures)}"
    )
    with (
        ThreadPoolExecutor(max_workers=args.workers) as pool,
        output_path.open("a", encoding="utf-8") as output_file,
        tqdm(total=chain_total, desc=f"KTO {split}", unit="chain", smoothing=0.1) as progress,
    ):
        written = completed
        for chunk in iter_chunks(
            input_path,
            split,
            completed,
            run_limit,
            args.chunk_size,
        ):
            futures: dict[Future[str], tuple[int, int]] = {}
            for record_index, (_record, system_prompt, input_text) in enumerate(chunk):
                for chain_id in range(args.num_results):
                    temperature = temperatures[chain_id]
                    future = pool.submit(
                        rewrite_chain,
                        client,
                        args.model,
                        system_prompt,
                        input_text,
                        args.rounds,
                        temperature,
                        args.max_tokens,
                        args.max_retries,
                    )
                    futures[future] = (record_index, chain_id)
            results: list[list[dict[str, object]]] = [[] for _item in chunk]
            first_error: Exception | None = None
            for future in as_completed(futures):
                record_index, chain_id = futures[future]
                try:
                    rewrite = future.result()
                except Exception as error:
                    first_error = first_error or error
                else:
                    results[record_index].append(
                        {
                            "chain_id": chain_id,
                            "temperature": temperatures[chain_id],
                            "rewrite": rewrite,
                        }
                    )
                progress.update(1)
            if first_error is not None:
                raise RuntimeError(
                    "one or more candidate chains failed after retries; current chunk was not written"
                ) from first_error
            for record_index, (seed_record, _system, _text) in enumerate(chunk):
                results[record_index].sort(key=lambda item: int(item["chain_id"]))
                output_record = {
                    "input_id": seed_record["input_id"],
                    "source": seed_record["source"],
                    "split": split,
                    "length_bucket": seed_record["length_bucket"],
                    "source_sha256": seed_record["source_sha256"],
                    "target_sha256": seed_record["target_sha256"],
                    "pair_sha256": seed_record["pair_sha256"],
                    "rounds": args.rounds,
                    "num_results": args.num_results,
                    "results": results[record_index],
                }
                validate_candidate_record(
                    output_record,
                    seed_record,
                    split,
                    args.num_results,
                    args.rounds,
                    temperatures,
                )
                output_file.write(
                    json.dumps(output_record, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
                written += 1
            output_file.flush()
    return written


def generation_parameters(args: argparse.Namespace) -> dict[str, object]:
    """Return the experiment parameters pinned for new-run and resume checks."""
    return {
        "base_url": args.base_url,
        "model": args.model,
        "rounds": args.rounds,
        "num_results": args.num_results,
        "temperatures": list(
            parse_temperature_schedule(args.temperatures, args.num_results)
        ),
        "max_tokens": args.max_tokens,
        "workers": args.workers,
        "chunk_size": args.chunk_size,
        "max_retries": args.max_retries,
        "enable_thinking": False,
        "prompt_policy": "use-each-seed-system-and-user-message",
        "whitespace_policy": "strip-boundaries-preserve-internal-paragraphs",
    }


def create_or_resume_bundle(
    args: argparse.Namespace,
    inputs: Mapping[str, Mapping[str, object]],
) -> tuple[Path, dict[str, object]]:
    """Create a timestamped run contract or validate an exact resume contract."""
    parameters = generation_parameters(args)
    if args.resume_bundle is not None:
        bundle = args.resume_bundle.resolve()
        run_path = bundle / "generation_run.yaml"
        run = load_yaml_mapping(run_path, "generation run")
        if run.get("inputs") != dict(inputs):
            raise ValueError("resume inputs differ from generation_run.yaml")
        if run.get("parameters") != parameters:
            raise ValueError("resume parameters differ from generation_run.yaml")
        if run.get("status") not in {"in_progress", "partial"}:
            raise ValueError("only in_progress or partial generation bundles can resume")
        return bundle, run

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle = args.output_dir.resolve() / f"kto_candidate_generation_{timestamp}"
    bundle.mkdir(parents=True, exist_ok=False)
    run = {
        "schema_version": 1,
        "version_id": args.manifest.resolve().parent.name,
        "status": "in_progress",
        "created_at": datetime.now().astimezone().isoformat(),
        "inputs": dict(inputs),
        "parameters": parameters,
        "script": {
            "path": "code/data_process/c_generate_kto_candidates.py",
            "sha256": sha256_file(Path(__file__)),
        },
    }
    with (bundle / "generation_run.yaml").open("x", encoding="utf-8") as output_file:
        yaml.safe_dump(run, output_file, allow_unicode=True, sort_keys=False)
    return bundle, run


def file_metadata(path: Path, record_count: int) -> dict[str, object]:
    """Return path, count, size, and SHA-256 for one completed output."""
    return {
        "path": str(path.resolve()),
        "record_count": record_count,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def register_completed_run(
    manifest_path: Path,
    bundle: Path,
    run: Mapping[str, object],
    run_sha256: str,
) -> None:
    """Register one complete candidate-generation artifact in the version manifest."""
    manifest = load_yaml_mapping(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    version_dir = manifest_path.resolve().parent
    relative_bundle = str(bundle.resolve().relative_to(version_dir))
    if any(
        isinstance(artifact, dict)
        and isinstance(artifact.get("parameters"), dict)
        and artifact["parameters"].get("bundle_path") == relative_bundle
        for artifact in artifacts["processed_data"]
    ):
        raise ValueError("candidate-generation bundle is already registered")
    outputs = run.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get("train"), dict):
        raise ValueError("completed run outputs are invalid")
    train = outputs["train"]
    relative_outputs: dict[str, object] = {}
    for split, metadata in outputs.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"completed {split} output metadata is invalid")
        relative_metadata = dict(metadata)
        relative_metadata["path"] = str(
            Path(str(metadata["path"])).resolve().relative_to(version_dir)
        )
        relative_outputs[str(split)] = relative_metadata
    artifact = {
        "id": bundle.name.replace("_", "-"),
        "status": "generated-pending-negative-selection-and-human-review",
        "purpose": "multi-candidate-generation-for-disjoint-kto-seeds",
        "source_id": "crawl-private-sft-snapshot",
        "path": str(Path(str(train["path"])).resolve().relative_to(version_dir)),
        "statistics_path": f"{relative_bundle}/generation_run.yaml",
        "format": "aligned-multi-candidate-jsonl",
        "created_at": run.get("finished_at"),
        "record_count": train.get("record_count"),
        "size_bytes": train.get("size_bytes"),
        "sha256": train.get("sha256"),
        "statistics_sha256": run_sha256,
        "parameters": {
            "bundle_path": relative_bundle,
            "generation": run.get("parameters"),
            "outputs": relative_outputs,
        },
    }
    artifacts["processed_data"].append(artifact)
    planned = manifest.get("planned_training")
    if isinstance(planned, dict) and isinstance(planned.get("stages"), list):
        for stage in planned["stages"]:
            if isinstance(stage, dict) and stage.get("name") == "kto-candidate-refresh-v2":
                stage["status"] = "completed"
    with manifest_path.open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(manifest, output_file, allow_unicode=True, sort_keys=False)


def main() -> int:
    """Generate both KTO splits, preserving exact identities for later selection."""
    args = parse_args()
    print("target: kto-candidate-generate")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        validate_parameters(args)
        manifest = load_yaml_mapping(args.manifest, "manifest")
        version = manifest.get("version")
        if not isinstance(version, dict) or version.get("status") == "released":
            raise ValueError("released or invalid version cannot start generation")
        inputs = {
            "train": source_metadata(args.train_input.resolve(), "train"),
            "validation": source_metadata(args.validation_input.resolve(), "validation"),
        }
        if args.limit_per_split <= 0:
            expected = {"train": 4500, "validation": 500}
            for split, count in expected.items():
                if inputs[split]["record_count"] != count:
                    raise ValueError(f"full {split} input count must equal {count}")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        bundle, run = create_or_resume_bundle(args, inputs)
        print(f"output_bundle: {bundle}")
        client = create_client(args.base_url, args.workers)
        output_counts: dict[str, int] = {}
        for split, input_path in (
            ("train", args.train_input.resolve()),
            ("validation", args.validation_input.resolve()),
        ):
            output_counts[split] = process_split(
                client,
                input_path,
                bundle / OUTPUT_NAMES[split],
                split,
                args,
                int(inputs[split]["record_count"]),
            )
        complete = all(
            output_counts[split] == inputs[split]["record_count"]
            for split in ("train", "validation")
        )
        run["status"] = "completed" if complete else "partial"
        run["finished_at"] = datetime.now().astimezone().isoformat()
        run["outputs"] = {
            split: file_metadata(bundle / OUTPUT_NAMES[split], output_counts[split])
            for split in ("train", "validation")
        }
        run_path = bundle / "generation_run.yaml"
        with run_path.open("w", encoding="utf-8") as output_file:
            yaml.safe_dump(run, output_file, allow_unicode=True, sort_keys=False)
        run_sha256 = sha256_file(run_path)
        if complete and args.limit_per_split <= 0:
            register_completed_run(args.manifest, bundle, run, run_sha256)
        print(f"train_record_count: {output_counts['train']}")
        print(f"validation_record_count: {output_counts['validation']}")
        print(f"generation_run_sha256: {run_sha256}")
        print(f"status: {'success' if complete else 'partial'}")
        print(f"finished_at: {run['finished_at']}")
        return 0
    except (OSError, RuntimeError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        print(f"finished_at: {datetime.now().astimezone().isoformat()}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
